from __future__ import annotations

import json

from meta_harness.memory_context_smoke import run_memory_context_smoke


def test_memory_context_smoke_compares_summary_verbatim_and_fusion(tmp_path):
    result = run_memory_context_smoke(
        run_id="run-memory-context",
        candidate_id="memory-context-fusion",
        data_dir=tmp_path,
    )

    assert result["passed"] is True
    assert result["provider_calls"] == 0
    assert result["comparison"]["winner_candidate_id"] == "memory-context-fusion"
    assert len(result["comparison"]["candidates"]) == 3
    candidates = {
        item["candidate_id"]: item for item in result["comparison"]["candidates"]
    }
    assert candidates["memory-context-fusion-hindsight-only"]["passed"] is True
    assert candidates["memory-context-fusion-hindsight-only"][
        "exact_evidence_available"
    ] is False
    assert candidates["memory-context-fusion-mempalace-verbatim"][
        "exact_evidence_available"
    ] is True
    assert candidates["memory-context-fusion"]["summary_available"] is True
    assert candidates["memory-context-fusion"]["fitness_score"] == 1.0

    run_dir = tmp_path / "runs" / "run-memory-context"
    comparison = json.loads(
        (run_dir / "memory_context_comparison.json").read_text(encoding="utf-8")
    )
    assert comparison["contract"] == "memory-context-comparison/v1"
    assert (run_dir / "candidates" / "memory-context-fusion" / "aggregate.json").exists()
    assert (
        run_dir
        / "candidates"
        / "memory-context-fusion-hindsight-only"
        / "aggregate.json"
    ).exists()
    assert (
        run_dir
        / "candidates"
        / "memory-context-fusion-mempalace-verbatim"
        / "aggregate.json"
    ).exists()
