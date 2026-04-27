"""Deterministic citation/support checks for retrieval answers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from retrieval.core.types import RetrievalHit

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = {
    "about",
    "also",
    "and",
    "are",
    "because",
    "but",
    "for",
    "from",
    "has",
    "have",
    "into",
    "not",
    "that",
    "the",
    "their",
    "this",
    "with",
}


@dataclass(frozen=True)
class CitationVerification:
    supported: bool
    unsupported_claims: tuple[str, ...]
    cited_reference_ids: tuple[str, ...]
    support_ratio: float


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in _WORD.findall(text)
        if len(token) > 2 and token.lower() not in _STOPWORDS
    }


def _sentences(answer: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_SPLIT.split(answer.strip()) if part.strip()]


def verify_context_support(
    answer: str,
    hits: list[RetrievalHit] | tuple[RetrievalHit, ...] | list[dict[str, Any]],
    *,
    min_overlap: float = 0.25,
) -> CitationVerification:
    """Check whether answer sentences are weakly supported by retrieved hits."""

    normalized_hits: list[RetrievalHit] = []
    for item in hits:
        if isinstance(item, RetrievalHit):
            normalized_hits.append(item)
        elif isinstance(item, dict):
            normalized_hits.append(RetrievalHit.from_mapping(item, default_source="retrieval"))

    evidence_tokens_by_id = {
        hit.id: _tokens(f"{hit.content} {hit.metadata}") for hit in normalized_hits
    }
    unsupported: list[str] = []
    cited_ids: set[str] = set()
    claims = _sentences(answer)

    for claim in claims:
        claim_tokens = _tokens(claim)
        if not claim_tokens:
            continue
        best_id = None
        best_overlap = 0.0
        for hit_id, evidence_tokens in evidence_tokens_by_id.items():
            if not evidence_tokens:
                continue
            overlap = len(claim_tokens & evidence_tokens) / max(len(claim_tokens), 1)
            if overlap > best_overlap:
                best_overlap = overlap
                best_id = hit_id
        if best_overlap >= min_overlap and best_id is not None:
            cited_ids.add(best_id)
        else:
            unsupported.append(claim)

    checked = max(len([claim for claim in claims if _tokens(claim)]), 1)
    support_ratio = (checked - len(unsupported)) / checked
    return CitationVerification(
        supported=not unsupported,
        unsupported_claims=tuple(unsupported),
        cited_reference_ids=tuple(sorted(cited_ids)),
        support_ratio=support_ratio,
    )
