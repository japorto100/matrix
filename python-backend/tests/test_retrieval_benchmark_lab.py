from __future__ import annotations

import json

import pytest

from retrieval.evals.benchmark_lab import (
    MATRIX_FUSED,
    MATRIX_KG_ONLY,
    MATRIX_VECTOR_ONLY,
    compare_candidates,
    write_benchmark_report,
)
from retrieval.evals.canaries import GENERAL_VECTOR_CANARY, TRADING_GEO_KG_CANARY


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


@pytest.mark.asyncio
async def test_write_benchmark_report_creates_meta_harness_artifact(tmp_path) -> None:
    report = await compare_candidates([GENERAL_VECTOR_CANARY], candidates=(MATRIX_VECTOR_ONLY,))
    path = write_benchmark_report(report, tmp_path / "retrieval" / "report.json")

    loaded = json.loads(path.read_text())

    assert loaded["feature_id"] == "022"
    assert loaded["candidates"][0]["candidate_id"] == "matrix-vector-only"
