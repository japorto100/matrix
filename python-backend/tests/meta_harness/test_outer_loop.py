from __future__ import annotations

import json

from meta_harness.outer_loop import (
    build_candidate_inventory,
    build_experience_packet,
    promotion_gate,
    write_candidate_manifest,
    write_pending_eval,
)


def test_candidate_manifest_requires_paper_artifacts(tmp_path):
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    candidate_dir.mkdir(parents=True)
    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "scores.json").write_text(
        json.dumps({"completion_rate": 1.0, "trace_gate_pass_rate": 1.0}),
        encoding="utf-8",
    )

    manifest = write_candidate_manifest(candidate_dir)

    assert manifest["paper_ready"] is False
    assert "missing-source-snapshot" in manifest["paper_failures"]
    assert "missing-raw-traces-or-benchmark-artifact" in manifest["paper_failures"]
    assert (candidate_dir / "candidate_manifest.json").exists()


def test_candidate_inventory_accepts_raw_trace_and_source_snapshot(tmp_path):
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)
    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "scores.json").write_text(
        json.dumps({"completion_rate": 1.0, "trace_gate_pass_rate": 1.0}),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps({"files": [{"path": "python-backend/agent/runners/simple.py"}]}),
        encoding="utf-8",
    )
    (trace_dir / "thread.json").write_text("[]", encoding="utf-8")

    inventory = build_candidate_inventory(candidate_dir)

    assert inventory.paper_ready is False
    assert inventory.trace_quality_failures == ("trace-empty",)
    assert inventory.has_raw_traces is True
    assert inventory.source_files[0]["path"] == "python-backend/agent/runners/simple.py"


def test_experience_packet_excludes_holdout_and_clusters_failures(tmp_path):
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)
    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "aggregate.json").write_text(
        json.dumps(
            {
                "completion_rate": 1.0,
                "trace_gate_pass_rate": 0.5,
                "fitness_score": 0.7,
                "tool_success_rate": 1.0,
                "failed_scenarios": [
                    {
                        "scenario_id": "scenario-1",
                        "failures": ["missing required memory route: fusion"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps({"files": [{"path": "python-backend/memory_fusion/provider.py"}]}),
        encoding="utf-8",
    )
    (trace_dir / "thread.json").write_text(
        json.dumps([{"action": "llm_response", "success": True}]),
        encoding="utf-8",
    )

    packet = build_experience_packet(data_dir=tmp_path, write_manifests=True)

    assert packet["holdout_policy"]["visible_to_proposer"] is False
    assert packet["candidate_count"] == 1
    assert packet["failure_clusters"][0]["failure"] == (
        "missing required memory route: fusion"
    )
    assert packet["next_proposer_actions"][0]["hypothesis"].startswith(
        "Memory/context candidate"
    )
    assert (candidate_dir / "candidate_manifest.json").exists()


def test_pending_eval_and_promotion_gate_fail_closed_without_holdout(tmp_path):
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)
    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "aggregate.json").write_text(
        json.dumps(
            {
                "completion_rate": 1.0,
                "trace_gate_pass_rate": 1.0,
                "fitness_score": 0.8,
            }
        ),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps({"files": [{"path": "python-backend/agent/runners/simple.py"}]}),
        encoding="utf-8",
    )
    (candidate_dir / "safety.json").write_text(
        json.dumps({"passed": True}),
        encoding="utf-8",
    )
    (trace_dir / "thread.json").write_text(
        json.dumps([{"action": "llm_response", "success": True}]),
        encoding="utf-8",
    )

    pending = write_pending_eval(
        run_id="run-1",
        candidate_id="candidate-a",
        candidate_type="code_patch",
        domain_id="agent-runtime-routing",
        write_scope=["python-backend/agent/runners/"],
        evaluation="search scenarios then holdout promotion gate",
        data_dir=tmp_path,
    )
    gate = promotion_gate(run_id="run-1", candidate_id="candidate-a", data_dir=tmp_path)

    assert pending["proposer_self_certification_allowed"] is False
    assert gate["passed"] is False
    assert "missing-holdout-verdict" in gate["failures"]


def test_promotion_gate_requires_search_stream_gates(tmp_path):
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)
    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "aggregate.json").write_text(
        json.dumps(
            {
                "completion_rate": 1.0,
                "trace_gate_pass_rate": 1.0,
                "stream_gate_pass_rate": 0.0,
                "fitness_score": 0.8,
            }
        ),
        encoding="utf-8",
    )
    (candidate_dir / "pending_eval.json").write_text(
        json.dumps({"evaluation": "frozen"}),
        encoding="utf-8",
    )
    (candidate_dir / "holdout.json").write_text(
        json.dumps(
            {
                "completion_rate": 1.0,
                "trace_gate_pass_rate": 1.0,
                "stream_gate_pass_rate": 1.0,
            }
        ),
        encoding="utf-8",
    )
    (candidate_dir / "safety.json").write_text(
        json.dumps({"passed": True}),
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

    gate = promotion_gate(run_id="run-1", candidate_id="candidate-a", data_dir=tmp_path)

    assert gate["passed"] is False
    assert "search-stream-gate-pass-rate-below-1.0" in gate["failures"]


def test_candidate_manifest_detects_holdout_payload_key(tmp_path):
    candidate_dir = tmp_path / "runs" / "run-1" / "candidates" / "candidate-a"
    trace_dir = candidate_dir / "traces" / "scenario-1"
    trace_dir.mkdir(parents=True)
    (tmp_path / "runs" / "run-1" / "run.json").write_text(
        json.dumps({"run_id": "run-1"}),
        encoding="utf-8",
    )
    (candidate_dir / "scores.json").write_text(
        json.dumps({"completion_rate": 1.0, "trace_gate_pass_rate": 1.0}),
        encoding="utf-8",
    )
    (candidate_dir / "source_snapshot.json").write_text(
        json.dumps({"files": [{"path": "python-backend/agent/runners/simple.py"}]}),
        encoding="utf-8",
    )
    (candidate_dir / "decision.json").write_text(
        json.dumps({"metrics": {"holdout_pass_rate": 1.0}}),
        encoding="utf-8",
    )
    (trace_dir / "thread.json").write_text(
        json.dumps([{"action": "llm_response", "success": True}]),
        encoding="utf-8",
    )

    manifest = write_candidate_manifest(candidate_dir)

    assert manifest["paper_ready"] is False
    assert "holdout-result-visible-to-proposer" in manifest["paper_failures"]
