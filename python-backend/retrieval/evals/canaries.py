"""Deterministic canary checks for hybrid RAG retrieval.

The canaries are not a replacement for RAGChecker/RAGAS/GraphRAG-Bench. They
are fast regression gates that keep Matrix's policy boundaries honest while the
real benchmark set is still small.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from retrieval.api import retrieve


@dataclass(frozen=True)
class CanaryExpectation:
    """Expected retrieval behavior for one canary query."""

    intent: str
    required_sources: tuple[str, ...] = ()
    forbidden_sources: tuple[str, ...] = ()
    must_not_degrade: bool = True
    required_reference_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalCanary:
    """One deterministic retrieval scenario with supplied candidates."""

    id: str
    query: str
    expectation: CanaryExpectation
    vector_hits: tuple[dict[str, Any], ...] = ()
    kg_hits: tuple[dict[str, Any], ...] = ()
    mode: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _observed_sources(hits: list[dict[str, Any]] | None) -> set[str]:
    sources: set[str] = set()
    for hit in hits or []:
        source = str(hit.get("source") or "")
        if source:
            sources.add(source)
        contributing = hit.get("metadata", {}).get("contributing_sources")
        if isinstance(contributing, list | tuple):
            sources.update(str(item) for item in contributing)
    return sources


async def evaluate_canary(canary: RetrievalCanary) -> dict[str, Any]:
    """Run one canary and return a stable pass/fail artifact."""

    result = await retrieve(
        canary.query,
        mode=canary.mode,
        vector_hits=list(canary.vector_hits),
        kg_hits=list(canary.kg_hits),
    )
    sources = _observed_sources(result.hits)
    reference_ids = {str(ref.get("id")) for ref in result.references or []}

    failures: list[str] = []
    if result.intent != canary.expectation.intent:
        failures.append(
            f"intent {result.intent!r} != expected {canary.expectation.intent!r}"
        )
    if canary.expectation.must_not_degrade and result.degraded:
        failures.append(f"degraded: {','.join(result.degraded_reasons or [])}")
    for required_source in canary.expectation.required_sources:
        if required_source not in sources:
            failures.append(f"missing source {required_source!r}")
    for forbidden_source in canary.expectation.forbidden_sources:
        if forbidden_source in sources:
            failures.append(f"forbidden source {forbidden_source!r}")
    for reference_id in canary.expectation.required_reference_ids:
        if reference_id not in reference_ids:
            failures.append(f"missing reference {reference_id!r}")

    return {
        "id": canary.id,
        "passed": not failures,
        "failures": failures,
        "intent": result.intent,
        "degraded": result.degraded,
        "degraded_reasons": result.degraded_reasons or [],
        "sources": sorted(sources),
        "reference_ids": sorted(reference_ids),
        "hit_count": len(result.hits or []),
    }


TRADING_GEO_KG_CANARY = RetrievalCanary(
    id="trading-geo-kg-001",
    query="How do EU sanctions affect Russian oil shipping insurance today?",
    expectation=CanaryExpectation(
        intent="temporal",
        required_sources=("kg", "vector"),
        required_reference_ids=("claim-sanctions-insurance",),
    ),
    vector_hits=(
        {
            "id": "chunk-shipping-brief",
            "text": "A shipping brief says tanker insurance became tighter this week.",
            "score": 0.83,
            "source_uri": "doc://shipping-brief",
        },
    ),
    kg_hits=(
        {
            "claim_id": "claim-sanctions-insurance",
            "content": "EU sanctions constrain Russian oil shipping insurance.",
            "score": 0.94,
            "metadata": {
                "path": ["EU", "SANCTIONS", "Russian oil", "SHIPPING_INSURANCE"]
            },
        },
    ),
)

GENERAL_VECTOR_CANARY = RetrievalCanary(
    id="general-vector-001",
    query="Summarize what this document says about quarterly revenue.",
    mode="text",
    expectation=CanaryExpectation(
        intent="text",
        required_sources=("vector",),
        forbidden_sources=("kg",),
        required_reference_ids=("chunk-revenue-summary",),
    ),
    vector_hits=(
        {
            "id": "chunk-revenue-summary",
            "text": "The document says quarterly revenue increased by 8 percent.",
            "score": 0.88,
            "source_uri": "doc://quarterly-report",
        },
    ),
    kg_hits=(
        {
            "claim_id": "claim-irrelevant-kg",
            "content": "An unrelated KG claim should not be used in text mode.",
            "score": 0.99,
        },
    ),
)
