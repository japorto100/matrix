from __future__ import annotations

import json

import pytest

from retrieval.evals.benchmark_lab import (
    MATRIX_FUSED,
    MATRIX_KG_ONLY,
    MATRIX_VECTOR_ONLY,
    RetrievalCandidate,
    compare_candidates,
    write_benchmark_report,
)
from retrieval.evals.canaries import (
    DEFAULT_CANARIES,
    DEFAULT_HOLDOUT_CANARIES,
    DEFAULT_SEARCH_CANARIES,
    GENERAL_VECTOR_CANARY,
    MULTIHOP_KG_HOLDOUT_CANARY,
    SIMPLE_DOC_HOLDOUT_CANARY,
    TRADING_GEO_KG_CANARY,
    CanaryExpectation,
    RetrievalCanary,
    canaries_for_split,
)


@pytest.mark.asyncio
async def test_compare_candidates_reports_vector_kg_and_fused_tradeoffs() -> None:
    report = await compare_candidates(
        [TRADING_GEO_KG_CANARY, GENERAL_VECTOR_CANARY],
        candidates=(MATRIX_VECTOR_ONLY, MATRIX_KG_ONLY, MATRIX_FUSED),
        k=5,
    )

    by_id = {candidate["candidate_id"]: candidate for candidate in report["candidates"]}

    assert report["feature_id"] == "022"
    assert by_id["matrix-vector-only"]["count"] == 2
    assert by_id["matrix-fused-vector-kg"]["pass_rate"] >= 0.5
    assert by_id["matrix-fused-vector-kg"]["recall@5"] == 1.0
    assert by_id["matrix-vector-only"]["recall@5"] < by_id["matrix-fused-vector-kg"]["recall@5"]
    assert by_id["matrix-kg-only"]["recall@5"] < by_id["matrix-fused-vector-kg"]["recall@5"]
    assert by_id["matrix-vector-only"]["results"][0]["passed"] is False
    assert by_id["matrix-kg-only"]["results"][1]["passed"] is False
    assert by_id["matrix-fused-vector-kg"]["metadata_compatibility"]["passed"] is True
    assert by_id["matrix-fused-vector-kg"]["split_summary"]["search"]["count"] == 2
    assert ["EU", "SANCTIONS", "Russian oil", "SHIPPING_INSURANCE"] in by_id[
        "matrix-fused-vector-kg"
    ]["results"][0]["kg_paths"]


@pytest.mark.asyncio
async def test_compare_candidates_separates_search_and_holdout_splits() -> None:
    report = await compare_candidates(
        DEFAULT_CANARIES,
        candidates=(MATRIX_VECTOR_ONLY, MATRIX_KG_ONLY, MATRIX_FUSED),
        k=5,
    )
    by_id = {candidate["candidate_id"]: candidate for candidate in report["candidates"]}

    assert report["splits"] == ["holdout", "search"]
    assert report["question_classes"] == [
        "multi_hop_temporal",
        "simple_document_grounded",
    ]
    assert canaries_for_split(DEFAULT_CANARIES, "search") == DEFAULT_SEARCH_CANARIES
    assert canaries_for_split(DEFAULT_CANARIES, "holdout") == DEFAULT_HOLDOUT_CANARIES
    assert by_id["matrix-fused-vector-kg"]["split_summary"]["holdout"]["count"] == 2
    assert by_id["matrix-fused-vector-kg"]["holdout_pass_rate"] >= 0.5
    assert by_id["matrix-vector-only"]["split_summary"]["holdout"]["pass_rate"] < by_id[
        "matrix-fused-vector-kg"
    ]["split_summary"]["holdout"]["pass_rate"]


@pytest.mark.asyncio
async def test_holdout_canaries_cover_graph_overreach_and_multihop_path() -> None:
    report = await compare_candidates(
        [SIMPLE_DOC_HOLDOUT_CANARY, MULTIHOP_KG_HOLDOUT_CANARY],
        candidates=(MATRIX_FUSED,),
        k=5,
    )
    results = report["candidates"][0]["results"]

    assert results[0]["split"] == "holdout"
    assert results[0]["question_class"] == "simple_document_grounded"
    assert results[0]["passed"] is True
    assert results[1]["question_class"] == "multi_hop_temporal"
    assert [
        "Red Sea",
        "DISRUPTS",
        "Shipping lanes",
        "AFFECTS",
        "EU diesel cracks",
    ] in results[1]["kg_paths"]


@pytest.mark.asyncio
async def test_compare_candidates_fails_missing_source_grounding_metadata() -> None:
    candidate = RetrievalCandidate(
        id="weak-baseline",
        mode="text",
        include_vector=True,
        include_kg=False,
        metadata={"source_corpus": "test"},
    )

    report = await compare_candidates([GENERAL_VECTOR_CANARY], candidates=(candidate,), k=5)
    result = report["candidates"][0]["results"][0]

    assert report["candidates"][0]["metadata_compatibility"]["passed"] is False
    assert result["passed"] is False
    assert "missing-candidate-metadata:parser_version" in result["failures"]


@pytest.mark.asyncio
async def test_compare_candidates_scores_citation_and_unsupported_claim_failures() -> None:
    canary = RetrievalCanary(
        id="citation-support-001",
        query="How do EU sanctions affect Russian oil exports?",
        expectation=CanaryExpectation(
            intent="graph",
            required_sources=("kg",),
            required_reference_ids=("claim-1",),
            required_cited_reference_ids=("claim-1",),
            generated_answer=(
                "EU sanctions affect Russian oil exports [claim-1]. "
                "Copper prices are guaranteed to rise."
            ),
            require_citations=True,
        ),
        kg_hits=(
            {
                "claim_id": "claim-1",
                "content": "EU sanctions affect Russian oil exports and shipping finance.",
                "score": 0.9,
            },
        ),
        mode="graph",
    )

    report = await compare_candidates([canary], candidates=(MATRIX_KG_ONLY,), k=5)
    result = report["candidates"][0]["results"][0]

    assert result["passed"] is False
    assert result["verification"]["citation_ratio"] == 1.0
    assert result["cited_reference_ids"] == ["claim-1"]
    assert any(
        failure.startswith("unsupported-claim:Copper prices are guaranteed to rise")
        for failure in result["failures"]
    )


@pytest.mark.asyncio
async def test_write_benchmark_report_creates_meta_harness_artifact(tmp_path) -> None:
    report = await compare_candidates([GENERAL_VECTOR_CANARY], candidates=(MATRIX_VECTOR_ONLY,))
    path = write_benchmark_report(report, tmp_path / "retrieval" / "report.json")

    loaded = json.loads(path.read_text())

    assert loaded["feature_id"] == "022"
    assert loaded["candidates"][0]["candidate_id"] == "matrix-vector-only"
