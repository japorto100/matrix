from __future__ import annotations

import asyncio
import json

from meta_harness import proposer


def test_load_recent_meta_harness_artifacts(tmp_path):
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "baseline"
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)

    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "scenario_set.json").write_text(
        json.dumps({"scenarios": [{"id": "scenario-1"}]}),
        encoding="utf-8",
    )
    (candidate_dir / "scores.json").write_text(
        json.dumps({"fitness_score": 0.7}),
        encoding="utf-8",
    )
    (candidate_dir / "verdicts.json").write_text(
        json.dumps({"passed": False, "failures": ["missing required tool: x"]}),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps({"files": [{"path": "python-backend/meta_harness/evaluator.py"}]}),
        encoding="utf-8",
    )
    (trace_dir / "thread-1.json").write_text(
        json.dumps(
            [
                {
                    "action": "tool_result",
                    "toolName": "memory_search",
                    "success": True,
                    "input": {"query": "risk"},
                }
            ]
        ),
        encoding="utf-8",
    )

    artifacts = proposer._load_recent_meta_harness_artifacts(data_dir=tmp_path)

    assert len(artifacts) == 1
    assert artifacts[0]["run"]["run_id"] == "run-1"
    assert artifacts[0]["verdicts"]["passed"] is False
    assert artifacts[0]["raw_trace_previews"][0]["timeline"][0]["tool"] == (
        "memory_search"
    )


def test_load_recent_candidate_decisions(monkeypatch):
    monkeypatch.setattr(
        "meta_harness.decisions.load_candidate_decisions",
        lambda limit=20: [{"decision": "defer", "candidate_id": "candidate-a"}],
    )

    decisions = proposer._load_recent_candidate_decisions()

    assert decisions[0]["decision"] == "defer"


def test_external_proposer_disabled_by_default(monkeypatch):
    monkeypatch.delenv(proposer.ENABLE_EXTERNAL_LLM_ENV, raising=False)

    result = asyncio.run(proposer.propose(model="openrouter/test", last_n_sessions=3))

    assert result["status"] == "disabled"
    assert result["external_llm_disabled"] is True
    assert result["required_env"] == proposer.ENABLE_EXTERNAL_LLM_ENV
    assert result["proposed_changes"] == []


def test_external_proposer_env_gate(monkeypatch):
    monkeypatch.delenv(proposer.ENABLE_EXTERNAL_LLM_ENV, raising=False)
    assert proposer._external_llm_enabled() is False

    monkeypatch.setenv(proposer.ENABLE_EXTERNAL_LLM_ENV, "true")
    assert proposer._external_llm_enabled() is True
