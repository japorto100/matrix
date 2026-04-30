"""Deterministic Meta-Harness lane for Feature 020 routing contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent.routing.delegation_policy import (
    build_delegation_defer_metadata,
    build_route_decision_metadata,
)
from meta_harness.scenario_runner import TraceExpectations, evaluate_trace_gates

DEFAULT_RUN_ID = "run-routing-contract"


def run_routing_contract_scenarios(
    *,
    run_id: str = DEFAULT_RUN_ID,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run provider-free route/delegation/loop-guard scenarios."""

    data_root = data_dir or Path(__file__).resolve().parents[2] / "data" / "meta_harness"
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        _no_tool_no_subagent(),
        _retrieval_beats_delegation(),
        _domain_delegate_deferred(),
        _tool_budget_exhaustion_fails_gate(),
        _provider_retry_loop_fails_gate(),
        _repeated_failed_tool_calls_fails_gate(),
        _forbidden_provider_and_secret_metadata_fails_gate(),
        _runtime_event_redaction_shape_gate(),
    ]
    passed = all(scenario["passed"] for scenario in scenarios)
    summary = {
        "run_id": run_id,
        "kind": "routing_contract",
        "feature_id": "020",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "scenario_count": len(scenarios),
        "passed_count": sum(1 for scenario in scenarios if scenario["passed"]),
        "scenarios": scenarios,
    }
    _write_json(run_dir / "routing_contract.json", summary)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "kind": "routing_contract",
            "feature_id": "020",
            "frontend_required": False,
            "provider_calls_required": False,
            "created_at": summary["created_at"],
        },
    )
    return {**summary, "artifact_path": str(run_dir / "routing_contract.json")}


def _scenario_result(
    *,
    scenario_id: str,
    verdict_passed: bool,
    expected_passed: bool,
    verdict: Any,
) -> dict[str, Any]:
    passed = verdict_passed is expected_passed
    return {
        "id": scenario_id,
        "passed": passed,
        "expected_gate_passed": expected_passed,
        "actual_gate_passed": verdict_passed,
        "failures": [] if passed else list(verdict.failures),
        "verdict": verdict.as_dict(),
    }


def _no_tool_no_subagent() -> dict[str, Any]:
    metadata = build_route_decision_metadata(
        runner="simple",
        tool_names=(),
        routing_reason="simple_turn",
    )
    verdict = evaluate_trace_gates(
        [{"action": "route_decision", "success": True, "metadata": metadata}],
        TraceExpectations(
            required_actions=("route_decision",),
            required_route_decisions=("direct_answer",),
            required_runner_variants=("simple",),
            required_delegation_decisions=("none",),
            max_spawn_depth=0,
        ),
    )
    return _scenario_result(
        scenario_id="routing-no-tool-no-subagent",
        verdict_passed=verdict.passed,
        expected_passed=True,
        verdict=verdict,
    )


def _retrieval_beats_delegation() -> dict[str, Any]:
    metadata = build_route_decision_metadata(
        runner="langgraph",
        tool_names=("memory_search",),
        routing_reason="retrieval_context_available",
        budget={"tool_calls_remaining": 4},
    )
    verdict = evaluate_trace_gates(
        [{"action": "route_decision", "success": True, "metadata": metadata}],
        TraceExpectations(
            required_actions=("route_decision",),
            required_route_decisions=("tool_use",),
            required_runner_variants=("langgraph",),
            required_delegation_decisions=("none",),
            required_event_metadata_keys={
                "route_decision": ("retrieval_route_requested", "budget.tool_calls_remaining")
            },
            max_spawn_depth=0,
        ),
    )
    route_ok = metadata["route_taxonomy"] == "retrieval_answer"
    return {
        **_scenario_result(
            scenario_id="routing-retrieval-beats-delegation",
            verdict_passed=verdict.passed and route_ok,
            expected_passed=True,
            verdict=verdict,
        ),
        "route_taxonomy": metadata["route_taxonomy"],
    }


def _domain_delegate_deferred() -> dict[str, Any]:
    metadata = build_delegation_defer_metadata(
        runner="dispatcher",
        delegate_kind="domain",
        requested_reason="portfolio_risk_review_requires_domain_delegate",
        max_spawn_depth=1,
        budget={"delegate_calls_remaining": 0},
    )
    verdict = evaluate_trace_gates(
        [{"action": "route_decision", "success": True, "metadata": metadata}],
        TraceExpectations(
            required_actions=("route_decision",),
            required_route_decisions=("defer",),
            required_delegation_decisions=("deferred",),
            required_event_metadata_keys={
                "route_decision": ("delegate_kind", "fallback_reason", "delegation_reason")
            },
            max_spawn_depth=0,
        ),
    )
    return _scenario_result(
        scenario_id="routing-domain-delegate-deferred",
        verdict_passed=verdict.passed,
        expected_passed=True,
        verdict=verdict,
    )


def _tool_budget_exhaustion_fails_gate() -> dict[str, Any]:
    events = [
        {
            "action": "tool_result",
            "toolName": "memory_search",
            "success": False,
            "metadata": {
                "tool_calls_total_limit": 1,
                "budget": {"remaining": 0, "exhausted": True},
            },
        }
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_event_metadata_keys={
                "tool_result": ("tool_calls_total_limit", "budget.exhausted")
            },
            min_tool_success_rate=1.0,
        ),
    )
    return _scenario_result(
        scenario_id="routing-tool-budget-exhaustion-fails",
        verdict_passed=verdict.passed,
        expected_passed=False,
        verdict=verdict,
    )


def _provider_retry_loop_fails_gate() -> dict[str, Any]:
    events = [
        {"action": "provider_retry", "success": False, "metadata": {"provider_retry": True}},
        {"action": "provider_retry", "success": False, "metadata": {"provider_retry": True}},
        {"action": "provider_retry", "success": False, "metadata": {"provider_retry": True}},
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(max_provider_retry_events=2),
    )
    return _scenario_result(
        scenario_id="routing-provider-retry-loop-fails",
        verdict_passed=verdict.passed,
        expected_passed=False,
        verdict=verdict,
    )


def _repeated_failed_tool_calls_fails_gate() -> dict[str, Any]:
    events = [
        {"action": "tool_result", "toolName": "kg_search", "success": False},
        {"action": "tool_result", "toolName": "kg_search", "success": False},
        {"action": "tool_result", "toolName": "kg_search", "success": False},
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(max_repeated_tool_failures_per_tool=2),
    )
    return _scenario_result(
        scenario_id="routing-repeated-failed-tool-calls-fails",
        verdict_passed=verdict.passed,
        expected_passed=False,
        verdict=verdict,
    )


def _forbidden_provider_and_secret_metadata_fails_gate() -> dict[str, Any]:
    events = [
        {
            "action": "route_decision",
            "success": True,
            "metadata": {
                "decision": "direct_answer",
                "runner": "simple",
                "delegation_decision": "none",
                "spawn_depth": 0,
                "provider_specific": {"reasoning_effort": "high"},
                "resolved_secret": "sk-test",
            },
        }
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            forbidden_event_metadata_keys={
                "route_decision": (
                    "provider_specific.reasoning_effort",
                    "resolved_secret",
                )
            }
        ),
    )
    return _scenario_result(
        scenario_id="routing-forbidden-provider-secret-metadata-fails",
        verdict_passed=verdict.passed,
        expected_passed=False,
        verdict=verdict,
    )


def _runtime_event_redaction_shape_gate() -> dict[str, Any]:
    events = [
        {
            "action": "llm_response",
            "success": True,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "llm.prompt_cache_break",
                        "metadata": {
                            "request_id": "req-cache-1",
                            "reasons": ("cache_read_tokens_dropped",),
                            "provider": "litellm",
                            "model": "provider/model",
                            "cache_read_tokens": 0,
                            "previous_cache_read_tokens": 128,
                        },
                    }
                ]
            },
        }
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_runtime_event_names=("llm.prompt_cache_break",),
            required_runtime_event_metadata_keys={
                "llm.prompt_cache_break": (
                    "request_id",
                    "reasons",
                    "provider",
                    "model",
                    "cache_read_tokens",
                    "previous_cache_read_tokens",
                )
            },
            forbidden_runtime_event_metadata_keys={
                "*": (
                    "api_key",
                    "authorization",
                    "headers",
                    "raw_prompt",
                    "request_telemetry",
                    "response.headers",
                    "resolved_secret",
                )
            },
        ),
    )
    return _scenario_result(
        scenario_id="routing-runtime-event-redaction-shape",
        verdict_passed=verdict.passed,
        expected_passed=True,
        verdict=verdict,
    )


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
