from __future__ import annotations

import json

import pytest

from meta_harness.decisions import (
    load_candidate_decisions,
    record_candidate_decision,
)


def test_record_candidate_decision_writes_global_run_and_candidate_logs(tmp_path):
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    candidate_dir.mkdir(parents=True)

    decision = record_candidate_decision(
        run_id="run-1",
        candidate_id="candidate-a",
        decision="discard",
        rationale="Holdout regression.",
        metrics={"holdout_pass_rate": 0.5},
        follow_up="Inspect memory recall trace.",
        data_dir=tmp_path,
    )

    assert decision.decision == "discard"
    assert (tmp_path / "candidate_decisions.jsonl").exists()
    assert (tmp_path / "runs" / "run-1" / "candidate_decisions.jsonl").exists()
    candidate_decision = json.loads((candidate_dir / "decision.json").read_text())
    assert candidate_decision["rationale"] == "Holdout regression."

    loaded = load_candidate_decisions(data_dir=tmp_path)
    assert loaded[0]["candidate_id"] == "candidate-a"


def test_record_candidate_decision_requires_rationale(tmp_path):
    with pytest.raises(ValueError, match="rationale"):
        record_candidate_decision(
            run_id="run-1",
            candidate_id="candidate-a",
            decision="keep",
            rationale="",
            data_dir=tmp_path,
        )
