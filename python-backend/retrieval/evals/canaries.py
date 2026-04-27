"""Deterministic canary checks for hybrid RAG retrieval.

The canaries are not a replacement for RAGChecker/RAGAS/GraphRAG-Bench. They
are fast regression gates that keep Matrix's policy boundaries honest while the
real benchmark set is still small.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import log2
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
    required_kg_paths: tuple[tuple[str, ...], ...] = ()
    generated_answer: str | None = None
    require_citations: bool = False
    required_cited_reference_ids: tuple[str, ...] = ()
    min_support_ratio: float = 1.0
    min_citation_ratio: float = 1.0


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


def _observed_kg_paths(hits: list[dict[str, Any]] | None) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    for hit in hits or []:
        path = hit.get("metadata", {}).get("path")
        if isinstance(path, list | tuple):
            normalized = tuple(str(part) for part in path if str(part))
            if normalized:
                paths.add(normalized)
    return paths


async def evaluate_canary(canary: RetrievalCanary) -> dict[str, Any]:
    """Run one canary and return a stable pass/fail artifact."""

    result = await retrieve(
        canary.query,
        mode=canary.mode,
        vector_hits=list(canary.vector_hits),
        kg_hits=list(canary.kg_hits),
        answer=canary.expectation.generated_answer,
        require_citations=canary.expectation.require_citations,
    )
    sources = _observed_sources(result.hits)
    kg_paths = _observed_kg_paths(result.hits)
    ranked_reference_ids = [str(ref.get("id")) for ref in result.references or []]
    reference_ids = set(ranked_reference_ids)
    verification = result.verification or {}
    cited_reference_ids = {
        str(ref_id) for ref_id in verification.get("cited_reference_ids", [])
    }

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
    for required_path in canary.expectation.required_kg_paths:
        if required_path not in kg_paths:
            failures.append(f"missing kg path {required_path!r}")
    for reference_id in canary.expectation.required_cited_reference_ids:
        if reference_id not in cited_reference_ids:
            failures.append(f"missing cited reference {reference_id!r}")
    if verification:
        if float(verification.get("support_ratio", 0.0)) < canary.expectation.min_support_ratio:
            failures.append(
                f"support ratio {verification.get('support_ratio')} "
                f"< {canary.expectation.min_support_ratio}"
            )
        if (
            float(verification.get("citation_ratio", 0.0))
            < canary.expectation.min_citation_ratio
        ):
            failures.append(
                f"citation ratio {verification.get('citation_ratio')} "
                f"< {canary.expectation.min_citation_ratio}"
            )
        for claim in verification.get("unsupported_claims", []):
            failures.append(f"unsupported claim {claim!r}")
        for claim in verification.get("missing_citation_claims", []):
            failures.append(f"missing citation for claim {claim!r}")

    return {
        "id": canary.id,
        "passed": not failures,
        "failures": failures,
        "intent": result.intent,
        "degraded": result.degraded,
        "degraded_reasons": result.degraded_reasons or [],
        "sources": sorted(sources),
        "kg_paths": [list(path) for path in sorted(kg_paths)],
        "ranked_reference_ids": ranked_reference_ids,
        "reference_ids": sorted(reference_ids),
        "verification": verification,
        "cited_reference_ids": sorted(cited_reference_ids),
        "hit_count": len(result.hits or []),
    }


async def evaluate_canary_set(
    canaries: tuple[RetrievalCanary, ...] | list[RetrievalCanary],
    *,
    k: int = 5,
) -> dict[str, Any]:
    """Aggregate deterministic retrieval canaries with Recall@k and nDCG@k."""

    results = [await evaluate_canary(canary) for canary in canaries]
    recall_values: list[float] = []
    ndcg_values: list[float] = []
    for canary, result in zip(canaries, results, strict=True):
        relevant = set(canary.expectation.required_reference_ids)
        if not relevant:
            continue
        ranked = [str(ref_id) for ref_id in result["ranked_reference_ids"][:k]]
        found = [ref_id for ref_id in ranked if ref_id in relevant]
        recall_values.append(len(set(found)) / len(relevant))
        dcg = sum(
            1.0 / log2(rank + 2)
            for rank, ref_id in enumerate(ranked)
            if ref_id in relevant
        )
        ideal = sum(1.0 / log2(rank + 2) for rank in range(min(len(relevant), k)))
        ndcg_values.append(dcg / ideal if ideal else 0.0)

    passed = sum(1 for result in results if result["passed"])
    return {
        "count": len(results),
        "passed": passed,
        "pass_rate": round(passed / max(len(results), 1), 4),
        f"recall@{k}": round(sum(recall_values) / max(len(recall_values), 1), 4),
        f"ndcg@{k}": round(sum(ndcg_values) / max(len(ndcg_values), 1), 4),
        "results": results,
    }


TRADING_GEO_KG_CANARY = RetrievalCanary(
    id="trading-geo-kg-001",
    query="How do EU sanctions affect Russian oil shipping insurance today?",
    expectation=CanaryExpectation(
        intent="temporal",
        required_sources=("kg", "vector"),
        required_reference_ids=("claim-sanctions-insurance",),
        required_kg_paths=(("EU", "SANCTIONS", "Russian oil", "SHIPPING_INSURANCE"),),
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
