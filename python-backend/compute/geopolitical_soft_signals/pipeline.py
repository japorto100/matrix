from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from math import log2
import os
import threading
import time
from typing import Literal

import httpx
from pydantic import BaseModel, Field

try:
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception:
    MiniBatchKMeans = None
    TfidfVectorizer = None

try:
    import sentence_transformers as _st_probe  # noqa: F401
    import hdbscan as _hdbscan_probe  # noqa: F401
    import numpy as _np_probe  # noqa: F401
    _EMBEDDING_AVAILABLE = True
except Exception:
    _EMBEDDING_AVAILABLE = False


SourceTier = Literal["A", "B", "C"]


class ArticleInput(BaseModel):
    title: str = Field(min_length=3)
    url: str = Field(min_length=8)
    publishedAt: str
    source: str
    summary: str | None = None


class SignalRequest(BaseModel):
    adapterId: str
    generatedAt: str
    articles: list[ArticleInput] = Field(default_factory=list)
    maxCandidates: int = Field(default=6, ge=1, le=20)


class SourceRefOutput(BaseModel):
    provider: str
    url: str
    title: str
    publishedAt: str
    sourceTier: SourceTier = "C"
    reliability: float = Field(default=0.6, ge=0.0, le=1.0)


class CandidateOutput(BaseModel):
    headline: str
    confidence: float = Field(default=0.45, ge=0.0, le=1.0)
    severityHint: int = Field(default=2, ge=1, le=5)
    regionHint: str = "global"
    countryHints: list[str] = Field(default_factory=list)
    sourceRefs: list[SourceRefOutput] = Field(default_factory=list)
    symbol: str | None = None
    category: str | None = None


class SignalResponse(BaseModel):
    candidates: list[CandidateOutput]


class IngestRawItem(BaseModel):
    source: str = "manual_import"
    title: str = Field(min_length=3)
    url: str = Field(min_length=4)
    content: str | None = None
    publishedAt: str | None = None
    lang: str | None = None


class IngestClassifyRequest(BaseModel):
    source: str = "manual_import"
    items: list[IngestRawItem] = Field(default_factory=list)
    maxCandidates: int = Field(default=6, ge=1, le=20)


ReviewAction = Literal["auto_route", "human_review", "auto_reject"]


class IngestClassifiedCandidate(BaseModel):
    headline: str
    confidence: float = Field(default=0.45, ge=0.0, le=1.0)
    severityHint: int = Field(default=2, ge=1, le=5)
    regionHint: str = "global"
    countryHints: list[str] = Field(default_factory=list)
    sourceRefs: list[SourceRefOutput] = Field(default_factory=list)
    symbol: str | None = None
    category: str | None = None
    routeTarget: Literal["geo", "macro", "trading", "research"] = "geo"
    reviewAction: ReviewAction = "human_review"
    dedupHash: str


class IngestClassifyResponse(BaseModel):
    success: bool = True
    source: str
    generatedAt: str
    classificationVersion: str = "uil-9b-v1"
    candidates: list[IngestClassifiedCandidate] = Field(default_factory=list)


@dataclass(frozen=True)
class ThemeRule:
    key: str
    tokens: tuple[str, ...]
    category: str
    symbol: str
    severity: int


THEMES: tuple[ThemeRule, ...] = (
    ThemeRule(
        key="sanctions",
        tokens=("sanction", "ofac", "export control", "embargo"),
        category="sanctions_export_controls",
        symbol="gavel",
        severity=3,
    ),
    ThemeRule(
        key="rates",
        tokens=("fomc", "ecb", "rate", "central bank", "inflation"),
        category="monetary_policy_rates",
        symbol="percent",
        severity=2,
    ),
    ThemeRule(
        key="conflict",
        tokens=("missile", "strike", "border", "war", "conflict", "troop"),
        category="military_conflict",
        symbol="shield-alert",
        severity=4,
    ),
    ThemeRule(
        key="energy",
        tokens=("pipeline", "oil", "gas", "opec", "lng"),
        category="energy_supply_shock",
        symbol="fuel",
        severity=3,
    ),
)

COUNTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "US": ("united states", "u.s.", "america", "federal reserve", "washington"),
    "GB": ("uk", "britain", "london", "england"),
    "DE": ("germany", "berlin", "bundesbank"),
    "FR": ("france", "paris"),
    "CN": ("china", "beijing", "pbo"),
    "RU": ("russia", "moscow", "kremlin"),
    "UA": ("ukraine", "kyiv", "kiev"),
    "IR": ("iran", "tehran"),
    "IL": ("israel", "jerusalem", "tel aviv"),
}

SOURCE_RELIABILITY: dict[str, tuple[SourceTier, float]] = {
    "reuters": ("A", 0.88),
    "bloomberg": ("A", 0.86),
    "ft": ("A", 0.84),
    "ap": ("A", 0.82),
    "wsj": ("A", 0.84),
    "cnbc": ("B", 0.74),
    "marketwatch": ("B", 0.72),
    "x.com": ("C", 0.52),
    "twitter": ("C", 0.52),
    "reddit": ("C", 0.5),
}

HAWKISH_TOKENS: tuple[str, ...] = (
    "escalation",
    "sanction",
    "conflict",
    "strike",
    "embargo",
    "war",
    "retaliation",
    "crackdown",
)

DOVISH_TOKENS: tuple[str, ...] = (
    "ceasefire",
    "de-escalation",
    "deescalation",
    "talks",
    "agreement",
    "relief",
    "easing",
    "truce",
)


_FINBERT_CACHE_LOCK = threading.Lock()
_FINBERT_CACHE: dict[str, tuple[float, float]] = {}


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw.strip())
        if value <= 0:
            return default
        return value
    except Exception:
        return default


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().split())


def detect_countries(text: str) -> list[str]:
    countries: list[str] = []
    for code, keywords in COUNTRY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            countries.append(code)
    return countries


def parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def source_ref(article: ArticleInput, provider_prefix: str) -> SourceRefOutput:
    source_key = normalize_text(article.source)
    tier, reliability = SOURCE_RELIABILITY.get(source_key, ("C", 0.62))
    provider = f"{provider_prefix}:{article.source}"
    if provider_prefix == "news_cluster" and env_flag("SOFT_SIGNAL_CHRONICLE_POC_ENABLED", False):
        provider = f"chronicle:{article.source}"
    elif provider_prefix == "social_surge" and env_flag("SOFT_SIGNAL_SCOUT_POC_ENABLED", False):
        provider = f"scout:{article.source}"
    elif provider_prefix == "narrative_shift" and env_flag("SOFT_SIGNAL_FINGPT_POC_ENABLED", False):
        provider = f"fingpt:{article.source}"

    return SourceRefOutput(
        provider=provider,
        url=article.url,
        title=article.title,
        publishedAt=article.publishedAt,
        sourceTier=tier,
        reliability=reliability,
    )


def confidence_from_count(count: int, base: float = 0.42) -> float:
    return max(0.0, min(1.0, base + min(0.28, count * 0.04)))


def recency_boost(published_at: str) -> float:
    published = parse_iso(published_at)
    age_hours = max(0.0, (datetime.now(timezone.utc) - published).total_seconds() / 3600.0)
    return max(0.0, 0.14 - min(0.14, age_hours * 0.004))


def _finbert_cache_key(text: str) -> str:
    normalized = normalize_text(text)[:1200]
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _finbert_cache_get(key: str, now: float) -> float | None:
    with _FINBERT_CACHE_LOCK:
        cached = _FINBERT_CACHE.get(key)
        if not cached:
            return None
        expires_at, score = cached
        if expires_at <= now:
            _FINBERT_CACHE.pop(key, None)
            return None
        return score


def _finbert_cache_put(key: str, score: float, now: float) -> None:
    ttl_seconds = env_int("FINBERT_HF_CACHE_TTL_MS", 600000) / 1000.0
    max_entries = env_int("FINBERT_HF_CACHE_MAX_ENTRIES", 2000)
    with _FINBERT_CACHE_LOCK:
        if len(_FINBERT_CACHE) >= max_entries:
            # FIFO-like eviction based on insertion order is sufficient here.
            oldest = next(iter(_FINBERT_CACHE), None)
            if oldest:
                _FINBERT_CACHE.pop(oldest, None)
        _FINBERT_CACHE[key] = (now + ttl_seconds, score)


def finbert_polarity_score(text: str) -> float | None:
    token = os.getenv("FINBERT_HF_API_TOKEN", "").strip()
    if not token:
        return None
    api_url = os.getenv(
        "FINBERT_HF_API_URL", "https://api-inference.huggingface.co/models/ProsusAI/finbert"
    ).strip()
    if not api_url:
        return None

    cache_key = _finbert_cache_key(text)
    now = time.time()
    cached = _finbert_cache_get(cache_key, now)
    if cached is not None:
        return cached

    timeout_seconds = env_int("FINBERT_HF_TIMEOUT_MS", 2500) / 1000.0

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                api_url,
                headers={"Authorization": f"Bearer {token}"},
                json={"inputs": text[:800]},
            )
            if response.status_code >= 400:
                return None
            payload = response.json()
            labels = payload[0] if isinstance(payload, list) and payload else []
            if not isinstance(labels, list):
                return None
            positive = 0.0
            negative = 0.0
            neutral = 0.0
            for item in labels:
                if not isinstance(item, dict):
                    continue
                label = normalize_text(str(item.get("label", "")))
                score = float(item.get("score", 0.0))
                if "positive" in label:
                    positive = score
                elif "negative" in label:
                    negative = score
                elif "neutral" in label:
                    neutral = score
            if positive == 0.0 and negative == 0.0 and neutral == 0.0:
                return None
            # [-1, 1] where positive is bullish and negative is bearish.
            score = max(-1.0, min(1.0, positive - negative))
            _finbert_cache_put(cache_key, score, now)
            return score
    except Exception:
        return None


def average_finbert_sentiment(items: list[ArticleInput], max_items: int = 8) -> float | None:
    sample = items[:max_items]
    if not sample:
        return None

    scores: list[float] = []
    for article in sample:
        score = finbert_polarity_score(article_text(article))
        if score is not None:
            scores.append(score)
    if not scores:
        return None
    return sum(scores) / len(scores)


def article_text(article: ArticleInput) -> str:
    return normalize_text(f"{article.title} {article.summary or ''} {article.source}")


def title_fingerprint(value: str) -> str:
    compact = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in normalize_text(value))
    return " ".join(part for part in compact.split(" ") if len(part) >= 3)


def dedupe_articles(items: list[ArticleInput]) -> list[ArticleInput]:
    deduped: list[ArticleInput] = []
    seen: set[str] = set()
    for item in items:
        key = title_fingerprint(item.title)
        if not key or key in seen:
            continue
        deduped.append(item)
        seen.add(key)
    return deduped


def lexical_sentiment_score(text: str) -> float:
    hawkish = sum(1 for token in HAWKISH_TOKENS if token in text)
    dovish = sum(1 for token in DOVISH_TOKENS if token in text)
    if hawkish == 0 and dovish == 0:
        return 0.0
    scale = max(1, hawkish + dovish)
    return (hawkish - dovish) / scale


def average_sentiment(items: list[ArticleInput]) -> float:
    if not items:
        return 0.0
    scores = [lexical_sentiment_score(article_text(item)) for item in items]
    return sum(scores) / len(scores)


def classify_theme(text: str) -> ThemeRule:
    best_rule = THEMES[0]
    best_score = -1
    for rule in THEMES:
        score = sum(1 for token in rule.tokens if token in text)
        if score > best_score:
            best_score = score
            best_rule = rule
    return best_rule


class NLPClusterRequest(BaseModel):
    texts: list[str] = Field(min_length=1)
    min_cluster_size: int = Field(default=2, ge=2, le=50)


class NLPClusterResponse(BaseModel):
    clusters: dict[int, list[str]]
    noise_count: int


def cluster_narratives_embedding(texts: list[str], min_cluster_size: int = 2) -> dict:
    """Cluster texts using sentence-transformers embeddings + HDBSCAN.

    Returns {"clusters": {label: [text, ...]}, "noise_count": N}.
    Raises ImportError if sentence-transformers or hdbscan are not installed.
    """
    if not _EMBEDDING_AVAILABLE:
        raise ImportError("sentence-transformers and hdbscan are required for embedding clustering")
    from sentence_transformers import SentenceTransformer
    import hdbscan
    import numpy as np

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)
    clusters: dict[int, list[str]] = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(texts[idx])
    return {"clusters": clusters, "noise_count": int(np.sum(labels == -1))}


def _build_candidates_from_buckets(
    buckets: dict[int, list[ArticleInput]], max_candidates: int
) -> list[CandidateOutput]:
    ranked_clusters = sorted(buckets.values(), key=lambda group: len(group), reverse=True)
    candidates: list[CandidateOutput] = []
    for group in ranked_clusters[:max_candidates]:
        primary = sorted(group, key=lambda item: parse_iso(item.publishedAt), reverse=True)[0]
        text = article_text(primary)
        theme = classify_theme(text)
        unique_sources = len({normalize_text(item.source) for item in group})
        confidence = confidence_from_count(len(group), 0.5) + min(0.1, unique_sources * 0.02)
        confidence += recency_boost(primary.publishedAt)
        refs = [source_ref(item, "news_cluster") for item in group[:2]]
        candidates.append(
            CandidateOutput(
                headline=f"{theme.key.title()} cluster detected: {primary.title}",
                confidence=max(0.0, min(1.0, confidence)),
                severityHint=theme.severity,
                regionHint="global",
                countryHints=detect_countries(text),
                sourceRefs=refs,
                symbol=theme.symbol,
                category=theme.category,
            )
        )
    return candidates


def build_news_cluster_ml(payload: SignalRequest) -> SignalResponse | None:
    if len(payload.articles) < 2:
        return None

    texts = [article_text(article) for article in payload.articles]

    # Phase 12a: Try embedding-based clustering first (sentence-transformers + HDBSCAN).
    # Falls back to TF-IDF/KMeans if not installed or on any runtime error.
    if _EMBEDDING_AVAILABLE and len(payload.articles) >= 2:
        try:
            result = cluster_narratives_embedding(texts, min_cluster_size=2)
            raw_clusters: dict[int, list[str]] = result["clusters"]
            # Map text back to ArticleInput (exclude noise label -1)
            text_to_article = {article_text(a): a for a in payload.articles}
            buckets: dict[int, list[ArticleInput]] = {}
            for label, cluster_texts in raw_clusters.items():
                if label == -1:
                    continue
                articles_in_cluster = [text_to_article[t] for t in cluster_texts if t in text_to_article]
                if articles_in_cluster:
                    buckets[label] = articles_in_cluster
            if buckets:
                candidates = _build_candidates_from_buckets(buckets, payload.maxCandidates)
                if candidates:
                    return SignalResponse(candidates=candidates)
        except Exception:
            pass  # Fall through to TF-IDF/KMeans

    # Fallback: TF-IDF/KMeans
    if TfidfVectorizer is None or MiniBatchKMeans is None:
        return None
    if len(payload.articles) < 4:
        return None

    n_clusters = max(1, min(payload.maxCandidates, min(6, len(payload.articles) // 2)))
    if n_clusters <= 1:
        return None

    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=1500)
        features = vectorizer.fit_transform(texts)
        model = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = model.fit_predict(features)
    except Exception:
        return None

    tfidf_buckets: dict[int, list[ArticleInput]] = {}
    for article, label in zip(payload.articles, labels):
        tfidf_buckets.setdefault(int(label), []).append(article)

    candidates = _build_candidates_from_buckets(tfidf_buckets, payload.maxCandidates)
    return SignalResponse(candidates=candidates) if candidates else None


def build_news_cluster(payload: SignalRequest) -> SignalResponse:
    working_payload = payload
    dedupe_ratio = 0.0
    if env_flag("SOFT_SIGNAL_CHRONICLE_POC_ENABLED", False):
        deduped_articles = dedupe_articles(payload.articles)
        if deduped_articles:
            dedupe_ratio = 1.0 - (len(deduped_articles) / max(1, len(payload.articles)))
            working_payload = payload.model_copy(update={"articles": deduped_articles})

    ml_result = build_news_cluster_ml(working_payload)
    if ml_result is not None and ml_result.candidates:
        if dedupe_ratio > 0:
            for candidate in ml_result.candidates:
                candidate.confidence = max(0.0, min(1.0, candidate.confidence + min(0.04, dedupe_ratio * 0.06)))
        return ml_result

    ranked = sorted(working_payload.articles, key=lambda item: parse_iso(item.publishedAt), reverse=True)
    buckets: dict[str, list[ArticleInput]] = {rule.key: [] for rule in THEMES}

    for article in ranked:
        text = normalize_text(f"{article.title} {article.summary or ''}")
        for rule in THEMES:
            if any(token in text for token in rule.tokens):
                buckets[rule.key].append(article)

    candidates: list[CandidateOutput] = []
    for rule in THEMES:
        grouped = buckets[rule.key]
        if not grouped:
            continue
        primary = grouped[0]
        text = normalize_text(f"{primary.title} {primary.summary or ''}")
        countries = detect_countries(text)
        unique_sources = len({normalize_text(item.source) for item in grouped})
        confidence = confidence_from_count(len(grouped), 0.48) + min(0.08, unique_sources * 0.02)
        confidence += min(0.04, dedupe_ratio * 0.06)
        confidence += recency_boost(primary.publishedAt)
        refs = [source_ref(item, "news_cluster") for item in grouped[:2]]
        headline_prefix = "Chronicle cluster" if env_flag("SOFT_SIGNAL_CHRONICLE_POC_ENABLED", False) else f"{rule.key.title()} cluster"
        candidates.append(
            CandidateOutput(
                headline=f"{headline_prefix} detected: {primary.title}",
                confidence=max(0.0, min(1.0, confidence)),
                severityHint=rule.severity,
                regionHint="global",
                countryHints=countries,
                sourceRefs=refs,
                symbol=rule.symbol,
                category=rule.category,
            )
        )

    return SignalResponse(candidates=candidates[: payload.maxCandidates])


def build_social_surge(payload: SignalRequest) -> SignalResponse:
    scout_mode = env_flag("SOFT_SIGNAL_SCOUT_POC_ENABLED", False)
    surge_articles: list[ArticleInput] = []
    source_counter: Counter[str] = Counter()
    for article in payload.articles:
        text = article_text(article)
        source_counter.update([article.source.lower()])
        if any(token in text for token in ("reddit", "x.com", "twitter", "viral", "trending", "surge")):
            surge_articles.append(article)
            continue
        if sum(1 for token in ("breaking", "urgent", "flash", "latest") if token in text) >= 2:
            surge_articles.append(article)

    if not surge_articles:
        return SignalResponse(candidates=[])

    distinct_sources = len({normalize_text(article.source) for article in surge_articles})
    top = sorted(surge_articles, key=lambda item: parse_iso(item.publishedAt), reverse=True)[: payload.maxCandidates]
    candidates: list[CandidateOutput] = []
    for article in top:
        text = normalize_text(f"{article.title} {article.summary or ''}")
        confidence = confidence_from_count(len(surge_articles) + source_counter[article.source.lower()], 0.44)
        confidence += min(0.08, distinct_sources * 0.015)
        confidence += recency_boost(article.publishedAt)
        if scout_mode:
            dominance = source_counter[article.source.lower()] / max(1, len(surge_articles))
            confidence += min(0.05, dominance * 0.05)
        finbert = finbert_polarity_score(text)
        if finbert is not None:
            confidence += min(0.06, abs(finbert) * 0.06)
        severity = 2 if finbert is None else (3 if abs(finbert) > 0.45 else 2)
        if scout_mode and distinct_sources >= 3 and len(surge_articles) >= 4:
            severity = max(severity, 3)
        refs = [source_ref(article, "social_surge")]
        if finbert is not None:
            refs[0].provider = f"{refs[0].provider}+finbert"
        candidates.append(
            CandidateOutput(
                headline=f"{'Scout surge' if scout_mode else 'Social surge'}: {article.title}",
                confidence=max(0.0, min(1.0, confidence)),
                severityHint=severity,
                regionHint="global",
                countryHints=detect_countries(text),
                sourceRefs=refs,
                symbol="message-circle-warning",
                category="social_chatter_surge",
            )
        )

    return SignalResponse(candidates=candidates)


def js_divergence(left: Counter[str], right: Counter[str]) -> float:
    keys = set(left.keys()) | set(right.keys())
    if not keys:
        return 0.0
    left_total = sum(left.values()) or 1
    right_total = sum(right.values()) or 1
    midpoint: dict[str, float] = {}
    for key in keys:
        p = left[key] / left_total
        q = right[key] / right_total
        midpoint[key] = (p + q) / 2

    def kl(counter: Counter[str], total: int) -> float:
        value = 0.0
        for key in keys:
            p = counter[key] / total
            if p > 0 and midpoint[key] > 0:
                value += p * log2(p / midpoint[key])
        return value

    return (kl(left, left_total) + kl(right, right_total)) / 2


def build_narrative_shift(payload: SignalRequest) -> SignalResponse:
    # TODO(Phase 23+): Real FinGPT/LLM narrative analysis → python-agent
    # (POST /api/v1/agent/narrative-shift). Currently FinBERT HTTP only — no LLM call.
    # Migration: python-compute calls python-agent via HTTP for the LLM-enhanced path.
    fingpt_mode = env_flag("SOFT_SIGNAL_FINGPT_POC_ENABLED", False)
    ranked = sorted(payload.articles, key=lambda item: parse_iso(item.publishedAt))
    if len(ranked) < 6:
        return SignalResponse(candidates=[])

    split_at = len(ranked) // 2
    older = ranked[:split_at]
    newer = ranked[split_at:]

    older_tokens: list[str] = []
    newer_tokens: list[str] = []

    for article in older:
        older_tokens.extend([token for token in article_text(article).split(" ") if len(token) >= 5])
    for article in newer:
        newer_tokens.extend([token for token in article_text(article).split(" ") if len(token) >= 5])

    older_counter = Counter(older_tokens)
    newer_counter = Counter(newer_tokens)
    drift_score = js_divergence(older_counter, newer_counter)
    older_sentiment = average_sentiment(older)
    newer_sentiment = average_sentiment(newer)
    sentiment_shift = newer_sentiment - older_sentiment
    finbert_shift = 0.0
    if fingpt_mode:
        older_finbert = average_finbert_sentiment(older)
        newer_finbert = average_finbert_sentiment(newer)
        if older_finbert is not None and newer_finbert is not None:
            finbert_shift = newer_finbert - older_finbert
            sentiment_shift += finbert_shift

    common = [
        token
        for token, count in newer_counter.most_common(50)
        if count >= 2 and count > older_counter.get(token, 0)
    ]
    if not common:
        return SignalResponse(candidates=[])

    top_articles = sorted(payload.articles, key=lambda item: parse_iso(item.publishedAt), reverse=True)
    candidates: list[CandidateOutput] = []
    for token in common[: payload.maxCandidates]:
        token_articles = [
            article
            for article in top_articles
            if token in normalize_text(f"{article.title} {article.summary or ''}")
        ]
        anchor = token_articles[0] if token_articles else None
        if anchor is None:
            continue
        source_count = len({normalize_text(article.source) for article in token_articles})
        confidence = max(0.35, min(0.95, 0.35 + drift_score * 0.5 + min(0.2, newer_counter[token] * 0.03)))
        confidence += min(0.08, source_count * 0.02)
        confidence += recency_boost(anchor.publishedAt)
        if fingpt_mode:
            confidence += min(0.08, abs(sentiment_shift) * 0.12)
            confidence += min(0.04, abs(finbert_shift) * 0.08)
        severity = 3 if fingpt_mode and abs(sentiment_shift) > 0.18 else 2
        refs = [source_ref(article, "narrative_shift") for article in token_articles[:2]]
        if fingpt_mode and finbert_shift != 0.0:
            for ref in refs:
                ref.provider = f"{ref.provider}+finbert"
        candidates.append(
            CandidateOutput(
                headline=f"{'FinGPT narrative shift' if fingpt_mode else 'Narrative shift'} around '{token}'",
                confidence=max(0.0, min(1.0, confidence)),
                severityHint=severity,
                regionHint="global",
                countryHints=detect_countries(normalize_text(f"{anchor.title} {anchor.summary or ''}")),
                sourceRefs=refs,
                symbol="brain-circuit",
                category="narrative_shift",
            )
        )

    return SignalResponse(candidates=candidates[: payload.maxCandidates])


def _ingest_items_to_signal_request(payload: IngestClassifyRequest) -> SignalRequest:
    items = payload.items[: payload.maxCandidates * 3]
    generated_at = datetime.now(timezone.utc).isoformat()
    if not items:
        return SignalRequest(adapterId="news_cluster", generatedAt=generated_at, articles=[], maxCandidates=payload.maxCandidates)

    articles: list[ArticleInput] = []
    for item in items:
        published_at = item.publishedAt or generated_at
        articles.append(
            ArticleInput(
                title=item.title,
                url=item.url,
                publishedAt=published_at,
                source=item.source,
                summary=item.content or "",
            )
        )
    adapter_id = normalize_text(payload.source)
    if "reddit" in adapter_id or "social" in adapter_id:
        adapter_id = "social_surge"
    elif "youtube" in adapter_id or "narrative" in adapter_id:
        adapter_id = "narrative_shift"
    else:
        adapter_id = "news_cluster"
    return SignalRequest(
        adapterId=adapter_id,
        generatedAt=generated_at,
        articles=articles,
        maxCandidates=payload.maxCandidates,
    )


def _route_target_for_category(category: str | None) -> Literal["geo", "macro", "trading", "research"]:
    value = normalize_text(category or "")
    if any(token in value for token in ("monetary", "rates", "inflation", "macro")):
        return "macro"
    if any(token in value for token in ("order", "market_microstructure", "trading", "signal")):
        return "trading"
    if any(token in value for token in ("research", "knowledge", "paper")):
        return "research"
    return "geo"


def _review_action_from_confidence(confidence: float) -> ReviewAction:
    if confidence >= 0.85:
        return "auto_route"
    if confidence >= 0.40:
        return "human_review"
    return "auto_reject"


def build_ingest_classification(payload: IngestClassifyRequest) -> IngestClassifyResponse:
    req = _ingest_items_to_signal_request(payload)
    if req.adapterId == "social_surge":
        raw = build_social_surge(req)
    elif req.adapterId == "narrative_shift":
        raw = build_narrative_shift(req)
    else:
        raw = build_news_cluster(req)

    generated_at = datetime.now(timezone.utc).isoformat()
    enriched: list[IngestClassifiedCandidate] = []
    for candidate in raw.candidates:
        source_url = candidate.sourceRefs[0].url if candidate.sourceRefs else ""
        dedup_hash = hashlib.sha256(f"{candidate.headline}|{source_url}".encode("utf-8")).hexdigest()
        enriched.append(
            IngestClassifiedCandidate(
                headline=candidate.headline,
                confidence=candidate.confidence,
                severityHint=candidate.severityHint,
                regionHint=candidate.regionHint,
                countryHints=candidate.countryHints,
                sourceRefs=candidate.sourceRefs,
                symbol=candidate.symbol,
                category=candidate.category,
                routeTarget=_route_target_for_category(candidate.category),
                reviewAction=_review_action_from_confidence(candidate.confidence),
                dedupHash=dedup_hash,
            )
        )

    return IngestClassifyResponse(
        source=payload.source,
        generatedAt=generated_at,
        candidates=enriched,
    )
