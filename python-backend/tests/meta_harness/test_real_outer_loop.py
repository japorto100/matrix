from __future__ import annotations

import json
from pathlib import Path

import pytest

from meta_harness import meta_cli, real_outer_loop


def _write_candidate_artifacts(
    *,
    data_dir: Path,
    run_id: str,
    candidate_id: str,
    completion_rate: float,
    trace_gate_pass_rate: float,
    fitness_score: float,
) -> None:
    candidate_dir = data_dir / "runs" / run_id / "candidates" / candidate_id
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)
    (data_dir / "runs" / run_id / "run.json").write_text(
        json.dumps({"run_id": run_id}),
        encoding="utf-8",
    )
    aggregate = {
        "run_id": run_id,
        "candidate_id": candidate_id,
        "scenarios_evaluated": 1,
        "completion_rate": completion_rate,
        "trace_gate_pass_rate": trace_gate_pass_rate,
        "stream_gate_pass_rate": 1.0,
        "fitness_score": fitness_score,
        "tool_success_rate": 1.0,
        "total_tokens": 1,
        "avg_duration_ms": 1,
        "failed_scenarios": []
        if trace_gate_pass_rate >= 1.0
        else [{"scenario_id": "s1", "failures": ["missing required memory route: fusion"]}],
    }
    (candidate_dir / "aggregate.json").write_text(json.dumps(aggregate), encoding="utf-8")
    (candidate_dir / "scores.json").write_text(json.dumps(aggregate), encoding="utf-8")
    (candidate_dir / "verdicts.json").write_text(
        json.dumps({"passed": trace_gate_pass_rate >= 1.0, "failures": aggregate["failed_scenarios"]}),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps({"files": [{"path": "python-backend/agent/runners/simple.py"}]}),
        encoding="utf-8",
    )
    (trace_dir / "thread.json").write_text(
        json.dumps([{"action": "llm_response", "success": True}]),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_real_outer_loop_runs_true_iteration(tmp_path, monkeypatch):
    scenario_path = tmp_path / "scenarios.json"
    scenario_path.write_text(json.dumps({"scenarios": []}), encoding="utf-8")

    async def _fake_run_scenario_file(path, **kwargs):
        candidate_id = kwargs["candidate_id"]
        if candidate_id == "baseline":
            metrics = (0.0, 0.0, 0.4)
        else:
            metrics = (1.0, 1.0, 0.9)
        _write_candidate_artifacts(
            data_dir=kwargs["data_dir"],
            run_id=kwargs["run_id"],
            candidate_id=candidate_id,
            completion_rate=metrics[0],
            trace_gate_pass_rate=metrics[1],
            fitness_score=metrics[2],
        )
        return {
            "run_id": kwargs["run_id"],
            "candidate_id": candidate_id,
            "scenarios_evaluated": 1,
            "completion_rate": metrics[0],
            "trace_gate_pass_rate": metrics[1],
            "stream_gate_pass_rate": 1.0,
            "fitness_score": metrics[2],
            "artifact_dir": str(
                kwargs["data_dir"] / "runs" / kwargs["run_id"] / "candidates" / candidate_id
            ),
        }

    monkeypatch.setattr(real_outer_loop, "run_scenario_file", _fake_run_scenario_file)

    result = await real_outer_loop.run_real_outer_loop(
        run_id="run-real",
        data_dir=tmp_path,
        scenario_path=scenario_path,
        iterations=1,
        max_scenarios=1,
    )

    candidate_dir = tmp_path / "runs" / "run-real" / "candidates" / "iter-001-config-overlay"
    assert result["true_meta_harness_iteration"] is True
    assert result["iteration_results"][0]["decision"]["decision"] == "keep"
    assert (candidate_dir / "proposal.json").exists()
    assert (candidate_dir / "pending_eval.json").exists()
    assert (candidate_dir / "proposer_interaction.json").exists()
    inspection = json.loads((candidate_dir / "proposer_interaction.json").read_text())
    assert inspection["files_read_count"] >= 3
    assert {"source", "scores", "trace"}.issubset(set(inspection["artifact_classes"]))
    assert (tmp_path / "runs" / "run-real" / "real_outer_loop_summary.json").exists()


@pytest.mark.asyncio
async def test_cli_outer_loop_dispatches_real_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(meta_cli, "_load_env_files", lambda: None)
    scenario_path = tmp_path / "scenarios.json"
    scenario_path.write_text(json.dumps({"scenarios": []}), encoding="utf-8")

    async def _fake_loop(**kwargs):
        assert kwargs["run_id"] == "run-cli-real"
        assert kwargs["scenario_path"] == scenario_path
        assert kwargs["data_dir"] == tmp_path
        return {"run_id": kwargs["run_id"], "true_meta_harness_iteration": True}

    monkeypatch.setattr("meta_harness.real_outer_loop.run_real_outer_loop", _fake_loop)
    args = meta_cli.build_parser().parse_args(
        [
            "outer-loop",
            "--run-id",
            "run-cli-real",
            "--scenario-path",
            str(scenario_path),
            "--data-dir",
            str(tmp_path),
        ]
    )

    result = await meta_cli._main_async(args)

    assert result["true_meta_harness_iteration"] is True

