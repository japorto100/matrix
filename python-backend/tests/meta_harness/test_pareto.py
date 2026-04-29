from __future__ import annotations

import json

from meta_harness import pareto


def test_load_meta_harness_candidates_from_aggregate(monkeypatch, tmp_path):
    candidate_dir = tmp_path / "run-1" / "candidates" / "baseline"
    candidate_dir.mkdir(parents=True)
    (candidate_dir / "aggregate.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "candidate_id": "baseline",
                "scenarios_evaluated": 2,
                "completion_rate": 1.0,
                "trace_gate_pass_rate": 0.5,
                "fitness_score": 0.75,
                "avg_turns": 1.0,
                "turn_efficiency": 1.0,
                "tool_success_rate": 1.0,
                "memory_utilization_rate": 0.5,
                "avg_tokens": 2000,
                "token_efficiency": 0.5,
                "total_cost_usd": 0.1,
                "avg_duration_ms": 250.0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pareto, "META_HARNESS_RUNS_DIR", tmp_path)

    candidates = pareto._load_meta_harness_candidates(set())

    assert len(candidates) == 1
    assert candidates[0]["version"] == "run-1:baseline"
    assert candidates[0]["source"] == "meta_harness"
    assert candidates[0]["trace_gate_pass_rate"] == 0.5
    assert candidates[0]["feasible"] is False
    assert candidates[0]["cost_efficiency"] > 0
    assert candidates[0]["latency_efficiency"] > 0


def test_load_meta_harness_candidates_falls_back_to_result_json(monkeypatch, tmp_path):
    candidate_dir = tmp_path / "run-legacy" / "candidates" / "baseline"
    candidate_dir.mkdir(parents=True)
    (candidate_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "run-legacy",
                "candidate_id": "baseline",
                "scenario_id": "s1",
                "turns": 1,
                "score": {
                    "completed": True,
                    "total_tokens": 1000,
                    "fitness_score": 1.0,
                    "memory_utilization": True,
                },
                "trace_verdict": {"passed": True, "tool_success_rate": None},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pareto, "META_HARNESS_RUNS_DIR", tmp_path)

    candidates = pareto._load_meta_harness_candidates(set())

    assert candidates[0]["completion_rate"] == 1.0
    assert candidates[0]["trace_gate_pass_rate"] == 1.0
    assert candidates[0]["memory_utilization_rate"] == 1.0


def test_frontier_prefers_non_dominated_candidate():
    candidates = [
        {
            "version": "bad",
            "trace_gate_pass_rate": 0.0,
            "completion_rate": 1.0,
            "fitness_score": 0.5,
            "turn_efficiency": 1.0,
            "tool_success_rate": 1.0,
            "memory_utilization_rate": 0.0,
            "token_efficiency": 0.1,
            "cost_efficiency": 0.9,
            "latency_efficiency": 1.0,
        },
        {
            "version": "good",
            "trace_gate_pass_rate": 1.0,
            "completion_rate": 1.0,
            "fitness_score": 1.0,
            "turn_efficiency": 1.0,
            "tool_success_rate": 1.0,
            "memory_utilization_rate": 1.0,
            "token_efficiency": 0.2,
            "cost_efficiency": 0.9,
            "latency_efficiency": 1.0,
        },
    ]

    frontier = pareto.compute_pareto_frontier(candidates)

    assert [c["version"] for c in frontier] == ["good"]


def test_frontier_filters_infeasible_token_efficient_failures():
    candidates = [
        {
            "version": "failed-cheap",
            "trace_gate_pass_rate": 0.0,
            "completion_rate": 0.0,
            "fitness_score": 0.0,
            "turn_efficiency": 1.0,
            "tool_success_rate": 1.0,
            "memory_utilization_rate": 0.0,
            "token_efficiency": 1000.0,
            "cost_efficiency": 1.0,
            "latency_efficiency": 1.0,
        },
        {
            "version": "passed-expensive",
            "trace_gate_pass_rate": 1.0,
            "completion_rate": 1.0,
            "fitness_score": 0.9,
            "turn_efficiency": 0.5,
            "tool_success_rate": 1.0,
            "memory_utilization_rate": 1.0,
            "token_efficiency": 0.1,
            "cost_efficiency": 0.1,
            "latency_efficiency": 0.1,
        },
    ]

    frontier = pareto.compute_pareto_frontier(candidates)

    assert [c["version"] for c in frontier] == ["passed-expensive"]


def test_frontier_does_not_reward_memory_when_trace_gates_match():
    candidates = [
        {
            "version": "no-unneeded-memory",
            "trace_gate_pass_rate": 1.0,
            "completion_rate": 1.0,
            "fitness_score": 0.9,
            "turn_efficiency": 1.0,
            "tool_success_rate": 1.0,
            "memory_utilization_rate": 0.0,
            "token_efficiency": 1.0,
            "cost_efficiency": 1.0,
            "latency_efficiency": 1.0,
        },
        {
            "version": "unneeded-memory",
            "trace_gate_pass_rate": 1.0,
            "completion_rate": 1.0,
            "fitness_score": 0.9,
            "turn_efficiency": 1.0,
            "tool_success_rate": 1.0,
            "memory_utilization_rate": 1.0,
            "token_efficiency": 1.0,
            "cost_efficiency": 1.0,
            "latency_efficiency": 1.0,
        },
    ]

    frontier = pareto.compute_pareto_frontier(candidates)

    assert {c["version"] for c in frontier} == {
        "no-unneeded-memory",
        "unneeded-memory",
    }


def test_normalize_candidate_records_feasibility_reasons():
    candidate = pareto._normalize_candidate(
        {
            "version": "partial",
            "completion_rate": 0.5,
            "trace_gate_pass_rate": 0.75,
        }
    )

    assert candidate["feasible"] is False
    assert candidate["feasibility_failures"] == [
        "completion_rate < 1.0",
        "trace_gate_pass_rate < 1.0",
    ]
