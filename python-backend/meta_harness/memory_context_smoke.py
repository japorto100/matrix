"""Deterministic Meta-Harness smoke for memory/context gates.

This runner deliberately avoids live provider calls. It feeds synthetic but
contract-shaped memory trace events through the same trace-gate and artifact
writer paths used by live Meta-Harness scenarios.
"""

from __future__ import annotations

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

    scenario = Scenario.from_mapping(
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
    trace_events = [
        {
            "action": "memory_recall",
            "threadId": "mh-memory-context-smoke",
            "success": True,
            "metadata": {
                "route": "fusion",
                "providers": "hindsight,mempalace",
                "bank_id": "project",
                "source": "memory_fusion",
                "evidence": (
                    "hindsight summary plus mempalace verbatim evidence before "
                    "compaction"
                ),
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
            "metadata": {"result_count": 2},
            "createdAt": now,
        },
        {
            "action": "memory_retain",
            "threadId": "mh-memory-context-smoke",
            "success": True,
            "metadata": {
                "route": "fusion",
                "providers": "hindsight,mempalace",
                "bank_id": "project",
                "source": "pre_compaction_presave",
            },
            "createdAt": now,
        },
    ]
    response = (
        "Use hindsight for learned summaries and mempalace for verbatim evidence "
        "before compaction."
    )
    verdict = evaluate_trace_gates(
        trace_events,
        scenario.expectations,
        response_text=response,
    )
    result = ScenarioRunResult(
        run_id=run_id,
        candidate_id=candidate_id,
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
            "fitness_score": 1.0 if verdict.passed else 0.0,
            "provider_calls": 0,
            "trace_gates": verdict.as_dict(),
        },
        trace_verdict=verdict,
    )
    artifact_dir = write_scenario_artifacts(result, scenario, data_dir=data_dir)
    aggregate = write_run_aggregate([result], data_dir=data_dir)
    return {
        "run_id": run_id,
        "candidate_id": candidate_id,
        "passed": verdict.passed,
        "failures": list(verdict.failures),
        "provider_calls": 0,
        "artifact_dir": str(artifact_dir),
        "aggregate": aggregate,
    }
