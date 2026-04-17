"""Skill Discovery — BM25 + optional dense hybrid (exec-skills Phase 1).

Env:
  AGENT_SKILL_FINDER=1|0     — default 1; 0 = skip ranking (caller passes all skills)
  AGENT_SKILL_FINDER_TOP_K=3
  AGENT_SKILL_FINDER_DENSE=1|0 — default 1; sentence-transformers cosine on name+desc+body preview
"""

from __future__ import annotations

import logging
import math
import os
import re
from functools import lru_cache

from agent.skills.loader import Skill

logger = logging.getLogger(__name__)

# RRF constant (common default)
_RRF_K = 60
# BM25 Okapi defaults
_BM25_K1 = 1.2
_BM25_B = 0.75


def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key, "").strip().lower()
    if v in ("", "default"):
        return default
    return v in ("1", "true", "yes", "on")


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _doc_text(skill: Skill, max_content_chars: int = 4000) -> str:
    body = (skill.content or "")[:max_content_chars]
    return f"{skill.name} {skill.description} {body}"


class _BM25:
    """Minimal Okapi BM25 over tokenized corpus."""

    def __init__(self, tokenized_docs: list[list[str]]) -> None:
        self._docs = tokenized_docs
        self._N = len(tokenized_docs)
        self._dl = [len(d) for d in tokenized_docs]
        self._avgdl = sum(self._dl) / self._N if self._N else 0.0
        df: dict[str, int] = {}
        for doc in tokenized_docs:
            seen = set(doc)
            for t in seen:
                df[t] = df.get(t, 0) + 1
        self._idf = {}
        for t, n in df.items():
            # idf = log((N - n + 0.5) / (n + 0.5) + 1)
            self._idf[t] = math.log((self._N - n + 0.5) / (n + 0.5) + 1.0)

    def scores(self, query: list[str]) -> list[float]:
        if not self._N or not self._avgdl:
            return [0.0] * self._N
        out: list[float] = []
        for i, doc in enumerate(self._docs):
            tf: dict[str, int] = {}
            for t in doc:
                tf[t] = tf.get(t, 0) + 1
            s = 0.0
            dl = self._dl[i]
            for t in query:
                if t not in tf:
                    continue
                idf = self._idf.get(t, 0.0)
                f = tf[t]
                num = f * (_BM25_K1 + 1)
                den = f + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / self._avgdl)
                s += idf * (num / den) if den else 0.0
            out.append(s)
        return out


def _rrf(rank_lists: list[list[int]], k: int = _RRF_K) -> dict[int, float]:
    """rank_lists: each is document indices ordered best-first. Returns index -> RRF score."""
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for r, doc_i in enumerate(ranks):
            scores[doc_i] = scores.get(doc_i, 0.0) + 1.0 / (k + r + 1)
    return scores


@lru_cache(maxsize=1)
def _sentence_transformer():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def _dense_ranks(skills: list[Skill], query: str) -> list[int]:
    texts = [_doc_text(s) for s in skills]
    try:
        import numpy as np
    except ImportError:
        logger.warning("numpy missing; dense skill ranking skipped")
        return list(range(len(skills)))

    try:
        model = _sentence_transformer()
    except ImportError:
        logger.warning("sentence_transformers missing; dense skill ranking skipped")
        return list(range(len(skills)))

    q_emb = model.encode(query, normalize_embeddings=True)
    doc_emb = model.encode(texts, normalize_embeddings=True)
    sims = np.dot(doc_emb, q_emb)
    order = list(np.argsort(-sims))
    return [int(x) for x in order]


def _bm25_ranks(skills: list[Skill], query: str) -> list[int]:
    toks = [tokenize(_doc_text(s)) for s in skills]
    q = tokenize(query)
    if not q:
        return list(range(len(skills)))
    bm = _BM25(toks)
    sc = bm.scores(q)
    order = sorted(range(len(skills)), key=lambda i: sc[i], reverse=True)
    return order


def find_skills_for_query(
    skills: list[Skill],
    query: str,
    *,
    top_k: int | None = None,
    max_tokens: int | None = None,
) -> list[Skill]:
    """Return up to top_k skills ranked by hybrid lexical+dense; empty query → all skills."""
    if not skills:
        return []
    q = (query or "").strip()
    if not q or not _env_bool("AGENT_SKILL_FINDER", True):
        return skills

    tk = top_k if top_k is not None else int(os.environ.get("AGENT_SKILL_FINDER_TOP_K", "3"))
    max_tok = max_tokens if max_tokens is not None else int(
        os.environ.get("AGENT_SKILL_FINDER_MAX_TOKENS", "2000")
    )

    bm_order = _bm25_ranks(skills, q)
    if _env_bool("AGENT_SKILL_FINDER_DENSE", True):
        dn_order = _dense_ranks(skills, q)
        rrf = _rrf([bm_order, dn_order])
    else:
        rrf = _rrf([bm_order])

    # Sort by RRF score desc
    idx_sorted = sorted(rrf.keys(), key=lambda i: rrf[i], reverse=True)

    picked: list[Skill] = []
    est = 0
    def approx_tok(text: str) -> int:
        return max(1, len(text) // 4)

    for i in idx_sorted:
        s = skills[i]
        block = f"{s.name}\n{s.description}\n{s.content}"
        cost = approx_tok(block)
        if picked and est + cost > max_tok:
            continue
        picked.append(s)
        est += cost
        if len(picked) >= tk:
            break

    if not picked:
        return skills[:tk]
    return picked


def filter_disabled_skills(skills: list[Skill], user_id: str | None) -> list[Skill]:
    """Remove skills explicitly disabled in agent.skills_state."""
    if not user_id:
        return skills
    from agent.skills.db_state import load_skill_toggle_overrides

    ov = load_skill_toggle_overrides(user_id)
    if not ov:
        return skills
    out: list[Skill] = []
    for s in skills:
        sid = f"{s.tier}:{s.name}"
        if sid in ov and not ov[sid]:
            continue
        out.append(s)
    return out if out else skills
