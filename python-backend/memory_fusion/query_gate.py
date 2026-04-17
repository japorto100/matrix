"""Query rewrite + verification gate for memory retrieval."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryGateDecision:
    action: str
    query: str
    reason: str
    needs_verification: bool
    degradation_flags: tuple[str, ...]


VERIFY_HINTS = (
    "verify",
    "ground truth",
    "beleg",
    "quelle",
    "source",
    "evidence",
    "web",
    "rag",
    "graphrag",
)


def decide_query_path(original_query: str, cleaned_query: str) -> QueryGateDecision:
    original = str(original_query or "").strip()
    cleaned = str(cleaned_query or "").strip()
    lowered = original.lower()
    needs_verification = any(token in lowered for token in VERIFY_HINTS)

    if not cleaned or len(cleaned) < 3:
        return QueryGateDecision(
            action="abstain",
            query="",
            reason="insufficient_query",
            needs_verification=needs_verification,
            degradation_flags=("MEMORY_QUERY_ABSTAINED",),
        )

    if cleaned != original:
        flags = ["MEMORY_QUERY_REWRITTEN"]
        if needs_verification:
            flags.append("MEMORY_VERIFY_REQUIRED")
        return QueryGateDecision(
            action="rewrite",
            query=cleaned,
            reason="sanitized_query",
            needs_verification=needs_verification,
            degradation_flags=tuple(flags),
        )

    if needs_verification:
        return QueryGateDecision(
            action="retrieve",
            query=cleaned,
            reason="verification_requested",
            needs_verification=True,
            degradation_flags=("MEMORY_VERIFY_REQUIRED",),
        )

    return QueryGateDecision(
        action="retrieve",
        query=cleaned,
        reason="default_retrieval",
        needs_verification=False,
        degradation_flags=(),
    )
