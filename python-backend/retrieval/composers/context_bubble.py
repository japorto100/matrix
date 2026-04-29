"""Context Bubble composer for compact RAG prompt context."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Any

from retrieval.core.types import ContextBubble, RetrievalHit

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]+")

SECTION_PRIORS: dict[str, float] = {
    "abstract": 1.08,
    "summary": 1.06,
    "results": 1.05,
    "table": 1.04,
    "claim": 1.03,
    "fulltext": 1.0,
    "body": 1.0,
    "appendix": 0.92,
    "references": 0.72,
    "bibliography": 0.72,
}
SOURCE_PRIORS: dict[str, float] = {
    "kg": 1.0,
    "fused": 1.0,
    "vector": 1.0,
}


def estimate_tokens(text: str) -> int:
    """Cheap token estimate used for deterministic context-budget tests."""

    return max(1, len(text) // 4)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _structural_prior(hit: RetrievalHit) -> float:
    metadata = hit.metadata if isinstance(hit.metadata, dict) else {}
    section = str(metadata.get("section") or metadata.get("chunk_section") or "").lower()
    status = str(metadata.get("status") or "").lower()
    context_metadata = metadata.get("context_metadata")
    if isinstance(context_metadata, dict):
        section = section or str(context_metadata.get("section") or "").lower()
        status = status or str(context_metadata.get("status") or "").lower()
    prior = SOURCE_PRIORS.get(hit.source, 1.0) * SECTION_PRIORS.get(section, 1.0)
    if status == "promoted":
        prior *= 1.05
    elif status in {"rejected", "superseded"}:
        prior *= 0.65
    confidence = _as_float(metadata.get("confidence"), 0.0)
    if confidence <= 0 and isinstance(context_metadata, dict):
        confidence = _as_float(context_metadata.get("confidence"), 0.0)
    if confidence > 0:
        prior *= 0.95 + min(confidence, 1.0) * 0.1
    return prior


def _embedding(hit: RetrievalHit) -> list[float] | None:
    value = hit.metadata.get("embedding") if isinstance(hit.metadata, dict) else None
    if not isinstance(value, list | tuple) or not value:
        return None
    vector: list[float] = []
    for item in value:
        try:
            vector.append(float(item))
        except (TypeError, ValueError):
            return None
    return vector


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _text_signature(text: str) -> set[str]:
    return {token.lower() for token in _WORD.findall(text) if len(token) > 2}


def _overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(min(len(a), len(b)), 1)


def _is_too_similar(
    candidate: RetrievalHit,
    selected: list[RetrievalHit],
    *,
    diversity_threshold: float,
) -> bool:
    candidate_embedding = _embedding(candidate)
    candidate_signature = _text_signature(candidate.content)
    for hit in selected:
        selected_embedding = _embedding(hit)
        if candidate_embedding is not None and selected_embedding is not None:
            if _cosine(candidate_embedding, selected_embedding) >= diversity_threshold:
                return True
        elif _overlap(candidate_signature, _text_signature(hit.content)) >= diversity_threshold:
            return True
    return False


def build_context_bubble(
    hits: Sequence[RetrievalHit],
    *,
    token_budget: int = 1600,
    max_hits: int = 8,
    diversity_threshold: float = 0.92,
) -> ContextBubble:
    """Build a source-attributed context block under a rough token budget.

    The composer keeps the API deterministic but adds two RAG-critical gates:
    structural priors lightly rerank candidates, and the diversity gate rejects
    near-duplicate content/embeddings before it consumes context budget.
    """

    selected: list[RetrievalHit] = []
    references: list[dict[str, object]] = []
    lines: list[str] = []
    used_tokens = 0
    ranked_hits = sorted(
        enumerate(hits),
        key=lambda item: (
            item[1].score * _structural_prior(item[1]),
            -item[0],
        ),
        reverse=True,
    )

    for _, hit in ranked_hits:
        content = " ".join(hit.content.split())
        if not content:
            continue
        if selected and _is_too_similar(
            hit,
            selected,
            diversity_threshold=diversity_threshold,
        ):
            continue
        label = f"[{len(selected) + 1}] {hit.source}"
        if hit.source_uri:
            label = f"{label} {hit.source_uri}"
        block = f"{label}\n{content}"
        cost = estimate_tokens(block)
        if selected and used_tokens + cost > token_budget:
            break
        selected.append(hit)
        lines.append(block)
        used_tokens += cost
        references.append(
            {
                "id": hit.id,
                "source": hit.source,
                "source_uri": hit.source_uri,
                "score": hit.score,
                "metadata": {
                    **hit.metadata,
                    "context_bubble": {
                        "rank": len(selected),
                        "selection_score": hit.score * _structural_prior(hit),
                        "structural_prior": _structural_prior(hit),
                    },
                },
            }
        )
        if len(selected) >= max_hits:
            break

    return ContextBubble(
        text="\n\n".join(lines),
        hits=tuple(selected),
        references=tuple(references),
    )
