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
    HIERARCHY_AWARE_DENSE_HOLDOUT_CANARY,
    MULTIHOP_KG_HOLDOUT_CANARY,
    NORNICDB_PROJECTION_CANARY,
    REPORT_GROUNDING_CANARY,
    SEMANTIC_TERM_CANARY,
    SIMPLE_DOC_HOLDOUT_CANARY,
    TRADING_GEO_KG_CANARY,
    URL_SOURCE_PROVENANCE_CANARY,
    VISUAL_LAYOUT_CANARY,
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
        "parser_hierarchy_grounded",
        "projection_replay",
        "report_grounding",
        "semantic_term_grounded",
        "simple_document_grounded",
        "source_provenance",
        "visual_layout_grounded",
    ]
    assert canaries_for_split(DEFAULT_CANARIES, "search") == DEFAULT_SEARCH_CANARIES
    assert canaries_for_split(DEFAULT_CANARIES, "holdout") == DEFAULT_HOLDOUT_CANARIES
    assert URL_SOURCE_PROVENANCE_CANARY in DEFAULT_SEARCH_CANARIES
    assert NORNICDB_PROJECTION_CANARY in DEFAULT_SEARCH_CANARIES
    assert by_id["matrix-fused-vector-kg"]["split_summary"]["holdout"]["count"] == 3
    assert by_id["matrix-fused-vector-kg"]["holdout_pass_rate"] >= 0.5
    assert by_id["matrix-vector-only"]["split_summary"]["holdout"]["pass_rate"] < by_id[
        "matrix-fused-vector-kg"
    ]["split_summary"]["holdout"]["pass_rate"]


@pytest.mark.asyncio
async def test_cross_feature_canaries_require_semantic_visual_and_report_metadata() -> None:
    report = await compare_candidates(
        [SEMANTIC_TERM_CANARY, VISUAL_LAYOUT_CANARY, REPORT_GROUNDING_CANARY],
        candidates=(MATRIX_VECTOR_ONLY, MATRIX_KG_ONLY, MATRIX_FUSED),
        k=5,
    )
    by_id = {candidate["candidate_id"]: candidate for candidate in report["candidates"]}

    vector_results = {
        result["canary_id"]: result for result in by_id["matrix-vector-only"]["results"]
    }
    kg_results = {
        result["canary_id"]: result for result in by_id["matrix-kg-only"]["results"]
    }
    fused_results = {
        result["canary_id"]: result for result in by_id["matrix-fused-vector-kg"]["results"]
    }

    assert by_id["matrix-vector-only"]["pass_rate"] == 1.0
    assert by_id["matrix-fused-vector-kg"]["pass_rate"] == 1.0
    assert by_id["matrix-kg-only"]["pass_rate"] == 0.0
    assert vector_results["semantic-term-tool-success-001"]["reference_metadata"][
        "chunk-semantic-tool-success-rate"
    ]["semantic_term_ids"] == ["agent_tool_success_rate", "tool_execution"]
    assert vector_results["visual-layout-source-coordinates-001"]["reference_metadata"][
        "chunk-visual-layout-table-cell"
    ]["bbox"] == [118, 248, 410, 286]
    assert fused_results["report-grounding-manifest-001"]["reference_metadata"][
        "chunk-report-rag-summary-citation"
    ]["report_manifest_id"] == "manifest-rag-benchmark-summary"
    assert "missing-source:vector" in kg_results["semantic-term-tool-success-001"][
        "failures"
    ]


@pytest.mark.asyncio
async def test_projection_replay_canary_requires_nornicdb_metadata() -> None:
    report = await compare_candidates(
        [NORNICDB_PROJECTION_CANARY],
        candidates=(MATRIX_KG_ONLY, MATRIX_VECTOR_ONLY),
        k=5,
    )
    by_id = {candidate["candidate_id"]: candidate for candidate in report["candidates"]}

    kg_result = by_id["matrix-kg-only"]["results"][0]
    vector_result = by_id["matrix-vector-only"]["results"][0]

    assert kg_result["passed"] is True
    assert kg_result["reference_metadata"]["claim-nornicdb-sanctions-insurance"][
        "projection_target"
    ] == "nornicdb"
    assert [
        "EU",
        "SANCTIONS",
        "Russian oil",
        "SHIPPING_INSURANCE",
    ] in kg_result["kg_paths"]
    assert vector_result["passed"] is False
    assert "missing-source:kg" in vector_result["failures"]


@pytest.mark.asyncio
async def test_holdout_canaries_cover_graph_overreach_and_multihop_path() -> None:
    report = await compare_candidates(
        [
            SIMPLE_DOC_HOLDOUT_CANARY,
            HIERARCHY_AWARE_DENSE_HOLDOUT_CANARY,
            MULTIHOP_KG_HOLDOUT_CANARY,
        ],
        candidates=(MATRIX_FUSED,),
        k=5,
    )
    results = report["candidates"][0]["results"]
    by_canary = {result["canary_id"]: result for result in results}

    assert results[0]["split"] == "holdout"
    assert results[0]["question_class"] == "simple_document_grounded"
    assert results[0]["passed"] is True
    assert by_canary["holdout-hierarchy-aware-parser-001"]["reference_metadata"][
        "chunk-researchwatcher-fall-height-formula"
    ]["chunker_name"] == "hierarchy-aware"
    assert by_canary["holdout-hierarchy-aware-parser-001"]["passed"] is True
    assert results[2]["question_class"] == "multi_hop_temporal"
    assert [
        "Red Sea",
        "DISRUPTS",
        "Shipping lanes",
        "AFFECTS",
        "EU diesel cracks",
    ] in results[2]["kg_paths"]


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
async def test_compare_candidates_fails_missing_reference_source_metadata() -> None:
    canary = RetrievalCanary(
        id="missing-reference-metadata-001",
        query="Which source metadata supports this chunk?",
        mode="text",
        expectation=CanaryExpectation(
            intent="text",
            required_sources=("vector",),
            required_reference_ids=("chunk-without-metadata",),
            required_reference_metadata={
                "chunk-without-metadata": ("source_artifact_id", "citation_ref")
            },
        ),
        vector_hits=(
            {
                "id": "chunk-without-metadata",
                "text": "This chunk intentionally has no citation metadata.",
                "score": 0.9,
                "source_uri": "doc://weak-source",
            },
        ),
    )

    report = await compare_candidates([canary], candidates=(MATRIX_VECTOR_ONLY,), k=5)
    result = report["candidates"][0]["results"][0]

    assert result["passed"] is False
    assert "missing-reference-metadata:chunk-without-metadata:source_artifact_id" in result[
        "failures"
    ]
    assert "missing-reference-metadata:chunk-without-metadata:citation_ref" in result[
        "failures"
    ]


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
