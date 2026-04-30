"""Deterministic Meta-Harness smoke for memory/context gates.

This runner deliberately avoids live provider calls. It feeds synthetic but
contract-shaped memory trace events through the same trace-gate and artifact
writer paths used by live Meta-Harness scenarios.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from meta_harness.proposer import META_HARNESS_DATA_DIR
from meta_harness.scenario_runner import (
    Scenario,
    ScenarioRunResult,
    evaluate_trace_gates,
    write_run_aggregate,
    write_scenario_artifacts,
)


def run_memory_context_smoke(
    *,
    run_id: str = "run-memory-context-smoke",
    candidate_id: str = "memory-context-deterministic",
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> dict[str, Any]:
    """Write deterministic memory/context Meta-Harness artifacts."""

    base_scenario = Scenario.from_mapping(
        {
            "id": "memory-context-fusion-smoke-001",
            "category": "memory_context_smoke",
            "turns": [
                {
                    "user": (
                        "Recall the compaction policy and cite the memory "
                        "evidence source."
                    )
                }
            ],
            "expected_trace": {
                "required_actions": ["memory_recall", "memory_retain"],
                "required_tools": ["memory_search"],
                "required_memory_routes": ["fusion"],
                "required_memory_providers": ["hindsight", "mempalace"],
                "required_response_terms": [
                    "verbatim evidence before compaction",
                    "hindsight",
                    "mempalace",
                ],
                "required_memory_evidence_terms": [
                    "verbatim evidence before compaction",
                    "hindsight",
                    "mempalace",
                ],
                "required_memory_metadata_keys": ["bank_id", "route", "source"],
                "expected_memory": True,
                "min_tool_success_rate": 1.0,
            },
            "metadata": {
                "provider_calls": 0,
                "purpose": "Feature 023 T044 memory/context smoke without live LLM",
            },
        }
    )
    now = datetime.now(UTC).isoformat()
    candidates = (
        {
            "candidate_id": f"{candidate_id}-hindsight-only",
            "route": "summary",
            "providers": "hindsight",
            "source": "hindsight_summary",
            "evidence": "hindsight summary says preserve evidence before compaction",
            "response": "Use hindsight for learned summaries before compaction.",
            "exact_evidence_available": False,
            "summary_available": True,
            "expected_providers": ("hindsight",),
            "expected_terms": ("hindsight", "compaction"),
            "fitness_score": 0.45,
        },
        {
            "candidate_id": f"{candidate_id}-mempalace-verbatim",
            "route": "verbatim",
            "providers": "mempalace",
            "source": "mempalace_verbatim",
            "evidence": "mempalace verbatim evidence before compaction",
            "response": "Use mempalace for verbatim evidence before compaction.",
            "exact_evidence_available": True,
            "summary_available": False,
            "expected_providers": ("mempalace",),
            "expected_terms": ("mempalace", "verbatim evidence before compaction"),
            "fitness_score": 0.78,
        },
        {
            "candidate_id": candidate_id,
            "route": "fusion",
            "providers": "hindsight,mempalace",
            "source": "memory_fusion",
            "evidence": (
                "hindsight summary plus mempalace verbatim evidence before "
                "compaction"
            ),
            "response": (
                "Use hindsight for learned summaries and mempalace for verbatim "
                "evidence before compaction."
            ),
            "exact_evidence_available": True,
            "summary_available": True,
            "expected_providers": ("hindsight", "mempalace"),
            "expected_terms": (
                "verbatim evidence before compaction",
                "hindsight",
                "mempalace",
            ),
            "fitness_score": 1.0,
        },
    )
    results: list[ScenarioRunResult] = []
    artifact_dirs: dict[str, str] = {}
    aggregates: dict[str, dict[str, Any]] = {}
    fixture_manifests: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        scenario = _candidate_scenario(base_scenario, candidate)
        trace_events = _candidate_trace_events(candidate, now=now)
        response = str(candidate["response"])
        verdict = evaluate_trace_gates(
            trace_events,
            scenario.expectations,
            response_text=response,
        )
        result = ScenarioRunResult(
            run_id=run_id,
            candidate_id=str(candidate["candidate_id"]),
            scenario_id=scenario.id,
            thread_id="mh-memory-context-smoke",
            user_id="meta-harness",
            category=scenario.category,
            turns=1,
            transcript=(
                {"role": "user", "content": scenario.turns[0].user},
                {"role": "assistant", "content": response},
            ),
            sse_chunks=(),
            trace_events=tuple(trace_events),
            score={
                "completed": verdict.passed,
                "memory_utilization": True,
                "tool_success_rate": verdict.tool_success_rate,
                "total_tokens": 0,
                "cost_estimate_usd": 0.0,
                "fitness_score": candidate["fitness_score"] if verdict.passed else 0.0,
                "provider_calls": 0,
                "exact_evidence_available": candidate["exact_evidence_available"],
                "summary_available": candidate["summary_available"],
                "memory_evidence_preservation_rate": (
                    1.0 if candidate["exact_evidence_available"] else 0.0
                ),
                "trace_gates": verdict.as_dict(),
            },
            trace_verdict=verdict,
        )
        results.append(result)
        artifact_dir = write_scenario_artifacts(result, scenario, data_dir=data_dir)
        artifact_dirs[result.candidate_id] = str(artifact_dir)
        fixture_manifests[result.candidate_id] = _write_memory_fixture_manifest(
            artifact_dir,
            run_id=run_id,
            candidate=candidate,
            scenario=scenario,
            trace_events=trace_events,
            created_at=now,
        )
        aggregates[result.candidate_id] = write_run_aggregate([result], data_dir=data_dir)

    comparison = _comparison_summary(results, aggregates)
    run_dir = data_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "memory_context_comparison.json").write_text(
        json.dumps(comparison, indent=2, default=str),
        encoding="utf-8",
    )
    (run_dir / "memory_fixture_manifest.json").write_text(
        json.dumps(
            {
                "contract": "memory-fixture-manifest/v1",
                "run_id": run_id,
                "created_at": now,
                "candidate_manifests": fixture_manifests,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "kind": "memory_context_smoke",
                "feature_id": "012",
                "frontend_required": False,
                "provider_calls_required": False,
                "candidate_count": len(results),
                "winner": comparison["winner_candidate_id"],
                "created_at": now,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    fusion_result = next(result for result in results if result.candidate_id == candidate_id)
    return {
        "run_id": run_id,
        "candidate_id": candidate_id,
        "passed": bool(comparison["passed"]),
        "failures": list(comparison["failures"]),
        "provider_calls": 0,
        "artifact_dir": artifact_dirs[candidate_id],
        "aggregate": aggregates[candidate_id],
        "comparison": comparison,
        "fixture_manifests": fixture_manifests,
        "candidate_results": [result.as_dict() for result in results],
        "trace_verdict": fusion_result.trace_verdict.as_dict(),
    }


def _candidate_scenario(
    base_scenario: Scenario,
    candidate: dict[str, Any],
) -> Scenario:
    return Scenario.from_mapping(
        {
            "id": f"{base_scenario.id}-{candidate['route']}",
            "category": base_scenario.category,
            "turns": [{"user": base_scenario.turns[0].user}],
            "expected_trace": {
                "required_actions": ["memory_recall", "memory_retain"],
                "required_tools": ["memory_search"],
                "required_memory_routes": [candidate["route"]],
                "required_memory_providers": list(candidate["expected_providers"]),
                "required_response_terms": list(candidate["expected_terms"]),
                "required_memory_evidence_terms": list(candidate["expected_terms"]),
                "required_memory_metadata_keys": [
                    "bank_id",
                    "route",
                    "source",
                    "source_status",
                    "raw_evidence_ref",
                    "operation_log_id",
                    "diff_ref",
                ],
                "expected_memory": True,
                "min_tool_success_rate": 1.0,
            },
            "metadata": {
                "provider_calls": 0,
                "candidate_route": candidate["route"],
                "purpose": (
                    "Feature 012 Hindsight/MemPalace/Fusion context-injection "
                    "comparison without live LLM"
                ),
            },
        }
    )


def _candidate_trace_events(
    candidate: dict[str, Any],
    *,
    now: str,
) -> list[dict[str, Any]]:
    base_metadata = {
        "route": candidate["route"],
        "providers": candidate["providers"],
        "bank_id": "project",
        "source": candidate["source"],
        "source_status": "durable",
        "raw_evidence_ref": "mempalace:drawer:turn-42",
        "operation_log_id": f"memory-op:{candidate['route']}:turn-42",
        "diff_ref": f"memory-diff:{candidate['route']}:turn-42",
    }
    return [
        {
            "action": "memory_recall",
            "threadId": "mh-memory-context-smoke",
            "success": True,
            "metadata": {
                **base_metadata,
                "evidence": candidate["evidence"],
            },
            "createdAt": now,
        },
        {
            "action": "tool_call",
            "threadId": "mh-memory-context-smoke",
            "toolName": "memory_search",
            "input": {"query": "verbatim evidence before compaction"},
            "success": True,
            "createdAt": now,
        },
        {
            "action": "tool_result",
            "threadId": "mh-memory-context-smoke",
            "toolName": "memory_search",
            "success": True,
            "metadata": {
                "result_count": 2,
                "result_keys": ("summary", "verbatim_text", "source_refs"),
            },
            "createdAt": now,
        },
        {
            "action": "memory_retain",
            "threadId": "mh-memory-context-smoke",
            "success": True,
            "metadata": {
                **base_metadata,
                "source": "pre_compaction_presave",
            },
            "createdAt": now,
        },
    ]


def _write_memory_fixture_manifest(
    artifact_dir: Path,
    *,
    run_id: str,
    candidate: dict[str, Any],
    scenario: Scenario,
    trace_events: list[dict[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    """Write a replayable fixture manifest next to scenario artifacts."""

    evidence = str(candidate.get("evidence") or "")
    manifest = {
        "contract": "memory-fixture-manifest/v1",
        "run_id": run_id,
        "candidate_id": str(candidate["candidate_id"]),
        "scenario_id": scenario.id,
        "created_at": created_at,
        "user_id": "meta-harness",
        "thread_id": "mh-memory-context-smoke",
        "bank_id": "project",
        "route": str(candidate["route"]),
        "providers": str(candidate["providers"]),
        "expected_providers": list(candidate["expected_providers"]),
        "expected_terms": list(candidate["expected_terms"]),
        "memory_refs": {
            "raw_evidence_ref": "mempalace:drawer:turn-42",
            "operation_log_id": f"memory-op:{candidate['route']}:turn-42",
            "diff_ref": f"memory-diff:{candidate['route']}:turn-42",
            "palace_path": "project/room/thread-42/turn-42",
        },
        "evidence": {
            "sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
            "preview": evidence[:240],
            "exact_evidence_available": bool(candidate["exact_evidence_available"]),
            "summary_available": bool(candidate["summary_available"]),
        },
        "trace_event_count": len(trace_events),
        "trace_actions": [str(event.get("action") or "") for event in trace_events],
        "replay": {
            "command": (
                "cd python-backend && uv run python -m meta_harness.meta_cli "
                f"memory-smoke --run-id {run_id}"
            ),
            "provider_calls_required": False,
            "frontend_required": False,
        },
    }
    (artifact_dir / "memory_fixture_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str),
        encoding="utf-8",
    )
    return manifest


def _comparison_summary(
    results: list[ScenarioRunResult],
    aggregates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for result in results:
        score = result.score
        rows.append(
            {
                "candidate_id": result.candidate_id,
                "passed": result.trace_verdict.passed,
                "fitness_score": score.get("fitness_score", 0.0),
                "exact_evidence_available": bool(
                    score.get("exact_evidence_available")
                ),
                "summary_available": bool(score.get("summary_available")),
                "memory_evidence_preservation_rate": score.get(
                    "memory_evidence_preservation_rate",
                    0.0,
                ),
                "aggregate": aggregates.get(result.candidate_id, {}),
            }
        )
    winner = max(rows, key=lambda row: float(row["fitness_score"]))
    failures: list[str] = []
    if not all(row["passed"] for row in rows):
        failures.append("memory-context-candidate-gate-failed")
    if not (
        winner["exact_evidence_available"] is True
        and winner["summary_available"] is True
    ):
        failures.append("fusion-candidate-did-not-win")
    return {
        "contract": "memory-context-comparison/v1",
        "passed": not failures,
        "failures": failures,
        "winner_candidate_id": winner["candidate_id"],
        "candidates": rows,
    }
