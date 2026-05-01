from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent import mcp_traces


@pytest.mark.asyncio
async def test_harness_run_scenarios_tool(monkeypatch):
    captured = {}

    async def _fake_run_scenario_file(path, **kwargs):
        captured["path"] = path
        captured.update(kwargs)
        return {"run_id": "run-1", "trace_gate_pass_rate": 1.0}

    monkeypatch.setattr(
        "meta_harness.scenario_runner.run_scenario_file",
        _fake_run_scenario_file,
    )

    raw = await mcp_traces.harness_run_scenarios(
        "/tmp/scenarios.json",
        max_scenarios=2,
        scenario_ids=["s1", "s3"],
        candidate_id="candidate-a",
        user_id="anonymous",
        model="test-model",
        agent_url="http://127.0.0.1:8094",
    )

    result = json.loads(raw)
    assert result["run_id"] == "run-1"
    assert captured["path"] == Path("/tmp/scenarios.json")
    assert captured["max_scenarios"] == 2
    assert captured["scenario_ids"] == ("s1", "s3")
    assert captured["candidate_id"] == "candidate-a"
    assert captured["user_id"] == "anonymous"
    assert captured["model"] == "test-model"
    assert captured["agent_url"] == "http://127.0.0.1:8094"


@pytest.mark.asyncio
async def test_harness_decide_candidate_tool(monkeypatch):
    captured = {}

    class _Decision:
        def as_dict(self):
            return {"decision": "keep", "candidate_id": "candidate-a"}

    def _fake_record_candidate_decision(**kwargs):
        captured.update(kwargs)
        return _Decision()

    monkeypatch.setattr(
        "meta_harness.decisions.record_candidate_decision",
        _fake_record_candidate_decision,
    )

    raw = await mcp_traces.harness_decide_candidate(
        "run-1",
        "candidate-a",
        "keep",
        "Improved trace gates.",
        metrics_json='{"trace_gate_pass_rate": 1.0}',
    )

    result = json.loads(raw)
    assert result["decision"] == "keep"
    assert captured["metrics"]["trace_gate_pass_rate"] == 1.0


@pytest.mark.asyncio
async def test_harness_evaluate_passes_split_and_holdout_flag(monkeypatch):
    captured = {}

    async def _fake_evaluate_search_set(**kwargs):
        captured.update(kwargs)
        return {"split": kwargs["split"], "queries_evaluated": 1}

    monkeypatch.setattr(
        "meta_harness.evaluator.evaluate_search_set",
        _fake_evaluate_search_set,
    )

    raw = await mcp_traces.harness_evaluate(
        max_queries=1,
        concurrency=2,
        use_cache=False,
        split="holdout",
        allow_holdout=True,
    )

    result = json.loads(raw)
    assert result["split"] == "holdout"
    assert captured["allow_holdout"] is True
    assert captured["concurrency"] == 2
