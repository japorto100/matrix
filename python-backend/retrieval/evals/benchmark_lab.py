"""Candidate comparison runner for Feature 022 RAG/KG benchmark lab."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import log2
from pathlib import Path
from time import perf_counter
from typing import Any

from retrieval.api import retrieve
from retrieval.evals.canaries import RetrievalCanary


@dataclass(frozen=True)
class RetrievalCandidate:
    """One retrieval mode candidate under matched canary budgets."""

    id: str
    mode: str | None
    include_vector: bool = True
    include_kg: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


_FIXTURE_METADATA: dict[str, Any] = {
    "source_corpus": "matrix-retrieval-canaries@2026-04-27",
    "parser_version": "deterministic-fixture/v1",
    "chunker_version": "deterministic-fixture/v1",
    "embedding_model": "deterministic-fixture",
    "embedding_dimension": 0,
}


MATRIX_VECTOR_ONLY = RetrievalCandidate(
    id="matrix-vector-only",
    mode="text",
    include_vector=True,
    include_kg=False,
    metadata={
        **_FIXTURE_METADATA,
        "feature": "019",
        "class": "baseline",
        "kg_projection_version": "disabled",
    },
)
MATRIX_KG_ONLY = RetrievalCandidate(
    id="matrix-kg-only",
    mode="graph",
    include_vector=False,
    include_kg=True,
    metadata={
        **_FIXTURE_METADATA,
        "feature": "017",
        "class": "baseline",
        "kg_projection_version": "postgres-fixture/v1",
    },
)
MATRIX_FUSED = RetrievalCandidate(
    id="matrix-fused-vector-kg",
    mode=None,
    include_vector=True,
    include_kg=True,
    metadata={
        **_FIXTURE_METADATA,
        "feature": "019/017",
        "class": "rrf",
        "kg_projection_version": "postgres-fixture/v1",
    },
)
DEFAULT_MATRIX_CANDIDATES = (MATRIX_VECTOR_ONLY, MATRIX_KG_ONLY, MATRIX_FUSED)
REQUIRED_CANDIDATE_METADATA = (
    "source_corpus",
    "parser_version",
    "chunker_version",
    "embedding_model",
    "embedding_dimension",
    "kg_projection_version",
)


def _sources(hits: list[dict[str, Any]] | None) -> set[str]:
    observed: set[str] = set()
    for hit in hits or []:
        source = hit.get("source")
        if source:
            observed.add(str(source))
        contributing = hit.get("metadata", {}).get("contributing_sources")
        if isinstance(contributing, list | tuple):
            observed.update(str(item) for item in contributing)
    return observed


def _kg_paths(hits: list[dict[str, Any]] | None) -> set[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    for hit in hits or []:
        path = hit.get("metadata", {}).get("path")
        if isinstance(path, list | tuple):
            normalized = tuple(str(part) for part in path if str(part))
            if normalized:
                paths.add(normalized)
    return paths


def _ranked_reference_ids(references: list[dict[str, Any]] | None) -> list[str]:
    return [str(ref.get("id")) for ref in references or []]


def _recall_at(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float | None:
    if not relevant_ids:
        return None
    return len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids)


def _ndcg_at(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float | None:
    if not relevant_ids:
        return None
    dcg = sum(
        1.0 / log2(rank + 2)
        for rank, ref_id in enumerate(ranked_ids[:k])
        if ref_id in relevant_ids
    )
    ideal = sum(1.0 / log2(rank + 2) for rank in range(min(len(relevant_ids), k)))
    return dcg / ideal if ideal else 0.0


def metadata_compatibility(candidate: RetrievalCandidate) -> dict[str, Any]:
    """Check if a candidate can be compared under source-grounded RAG gates."""
    missing = [
        key
        for key in REQUIRED_CANDIDATE_METADATA
        if candidate.metadata.get(key) in (None, "")
    ]
    failures = [f"missing-candidate-metadata:{key}" for key in missing]
    return {
        "passed": not failures,
        "required_keys": list(REQUIRED_CANDIDATE_METADATA),
        "missing_keys": missing,
        "failures": failures,
    }


async def evaluate_candidate(
    canary: RetrievalCanary,
    candidate: RetrievalCandidate,
    *,
    k: int = 5,
    token_budget: int = 1600,
    max_hits: int = 8,
) -> dict[str, Any]:
    """Run one candidate on one canary with deterministic metrics."""

    started = perf_counter()
    result = await retrieve(
        canary.query,
        mode=candidate.mode or canary.mode,
        vector_hits=list(canary.vector_hits) if candidate.include_vector else [],
        kg_hits=list(canary.kg_hits) if candidate.include_kg else [],
        token_budget=token_budget,
        max_hits=max_hits,
        answer=canary.expectation.generated_answer,
        require_citations=canary.expectation.require_citations,
    )
    latency_ms = round((perf_counter() - started) * 1000, 3)
    sources = _sources(result.hits)
    kg_paths = _kg_paths(result.hits)
    ranked_ids = _ranked_reference_ids(result.references)
    relevant = set(canary.expectation.required_reference_ids)
    compatibility = metadata_compatibility(candidate)
    verification = result.verification or {}
    cited_reference_ids = {
        str(ref_id) for ref_id in verification.get("cited_reference_ids", [])
    }
    failures: list[str] = list(compatibility["failures"])

    if result.degraded and canary.expectation.must_not_degrade:
        failures.append(f"degraded:{','.join(result.degraded_reasons or [])}")
    for required_source in canary.expectation.required_sources:
        if required_source not in sources:
            failures.append(f"missing-source:{required_source}")
    for forbidden_source in canary.expectation.forbidden_sources:
        if forbidden_source in sources:
            failures.append(f"forbidden-source:{forbidden_source}")
    for reference_id in relevant:
        if reference_id not in ranked_ids:
            failures.append(f"missing-reference:{reference_id}")
    for required_path in canary.expectation.required_kg_paths:
        if required_path not in kg_paths:
            failures.append(f"missing-kg-path:{' -> '.join(required_path)}")
    for reference_id in canary.expectation.required_cited_reference_ids:
        if reference_id not in cited_reference_ids:
            failures.append(f"missing-cited-reference:{reference_id}")
    if verification:
        if float(verification.get("support_ratio", 0.0)) < canary.expectation.min_support_ratio:
            failures.append(
                "support-ratio:"
                f"{verification.get('support_ratio')}<"
                f"{canary.expectation.min_support_ratio}"
            )
        if (
            float(verification.get("citation_ratio", 0.0))
            < canary.expectation.min_citation_ratio
        ):
            failures.append(
                "citation-ratio:"
                f"{verification.get('citation_ratio')}<"
                f"{canary.expectation.min_citation_ratio}"
            )
        failures.extend(
            f"unsupported-claim:{claim}"
            for claim in verification.get("unsupported_claims", [])
        )
        failures.extend(
            f"missing-citation:{claim}"
            for claim in verification.get("missing_citation_claims", [])
        )

    return {
        "canary_id": canary.id,
        "candidate_id": candidate.id,
        "passed": not failures,
        "failures": failures,
        "intent": result.intent,
        "degraded": result.degraded,
        "degraded_reasons": result.degraded_reasons or [],
        "metadata_compatibility": compatibility,
        "verification": verification,
        "cited_reference_ids": sorted(cited_reference_ids),
        "sources": sorted(sources),
        "kg_paths": [list(path) for path in sorted(kg_paths)],
        "ranked_reference_ids": ranked_ids,
        f"recall@{k}": _recall_at(ranked_ids, relevant, k),
        f"ndcg@{k}": _ndcg_at(ranked_ids, relevant, k),
        "hit_count": len(result.hits or []),
        "latency_ms": latency_ms,
    }


async def compare_candidates(
    canaries: list[RetrievalCanary] | tuple[RetrievalCanary, ...],
    *,
    candidates: tuple[RetrievalCandidate, ...] = DEFAULT_MATRIX_CANDIDATES,
    k: int = 5,
    token_budget: int = 1600,
    max_hits: int = 8,
) -> dict[str, Any]:
    """Run all candidates over a canary set and return an artifact-ready report."""

    report_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        results = [
            await evaluate_candidate(
                canary,
                candidate,
                k=k,
                token_budget=token_budget,
                max_hits=max_hits,
            )
            for canary in canaries
        ]
        compatibility = metadata_compatibility(candidate)
        recall_values = [
            result[f"recall@{k}"] for result in results if result[f"recall@{k}"] is not None
        ]
        ndcg_values = [
            result[f"ndcg@{k}"] for result in results if result[f"ndcg@{k}"] is not None
        ]
        passed = sum(1 for result in results if result["passed"])
        report_candidates.append(
            {
                "candidate_id": candidate.id,
                "mode": candidate.mode,
                "include_vector": candidate.include_vector,
                "include_kg": candidate.include_kg,
                "metadata": candidate.metadata,
                "metadata_compatibility": compatibility,
                "count": len(results),
                "passed": passed,
                "pass_rate": round(passed / max(len(results), 1), 4),
                f"recall@{k}": round(
                    sum(recall_values) / max(len(recall_values), 1), 4
                ),
                f"ndcg@{k}": round(sum(ndcg_values) / max(len(ndcg_values), 1), 4),
                "latency_ms_avg": round(
                    sum(result["latency_ms"] for result in results)
                    / max(len(results), 1),
                    3,
                ),
                "results": results,
            }
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "feature_id": "022",
        "k": k,
        "token_budget": token_budget,
        "max_hits": max_hits,
        "canary_count": len(canaries),
        "candidates": report_candidates,
    }


def write_benchmark_report(report: dict[str, Any], output_path: Path) -> Path:
    """Write a benchmark report as stable JSON for Meta-Harness artifacts."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return output_path
