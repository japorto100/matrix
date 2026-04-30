"""Deterministic Meta-Harness lane for Feature 020 routing contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent.routing.delegation_policy import (
    build_child_tool_policy,
    build_delegation_defer_metadata,
    build_route_decision_metadata,
)
from agent.runtime_events import make_runtime_event, runtime_event_name_matches_kind
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
        _llm_failure_runtime_event_gate(),
        _runtime_event_replay_identity_gate(),
        _runtime_event_taxonomy_gate(),
        _tool_hook_policy_trace_shape_gate(),
        _context_overflow_compress_retry_trace_gate(),
        _subagent_isolation_runtime_gate(),
        _subagent_forged_child_tools_filtered_gate(),
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


def _llm_failure_runtime_event_gate() -> dict[str, Any]:
    event = make_runtime_event(
        kind="llm",
        status="failed",
        name="llm.call.failed",
        summary="LLM call failed",
        thread_id="thread-routing",
        turn=2,
        metadata={
            "provider": "openrouter",
            "model": "openrouter/test-model",
            "error_type": "RateLimitError",
            "reason": "rate_limit",
            "recovery": "backoff_then_retry",
            "retryable": True,
            "status_code": 429,
        },
    )
    verdict = evaluate_trace_gates(
        [
            {
                "action": "llm_response",
                "success": False,
                "metadata": {"runtime_events": [event]},
            }
        ],
        TraceExpectations(
            required_runtime_event_names=("llm.call.failed",),
            required_runtime_event_metadata_keys={
                "llm.call.failed": (
                    "provider",
                    "model",
                    "error_type",
                    "reason",
                    "recovery",
                    "retryable",
                    "status_code",
                )
            },
            forbidden_runtime_event_metadata_keys={
                "*": ("raw_prompt", "messages", "api_key", "authorization")
            },
        ),
    )
    return _scenario_result(
        scenario_id="routing-llm-failure-runtime-event-shape",
        verdict_passed=verdict.passed,
        expected_passed=True,
        verdict=verdict,
    )


def _runtime_event_replay_identity_gate() -> dict[str, Any]:
    runtime_event = make_runtime_event(
        kind="tool",
        status="completed",
        name="tool.semantic_lookup",
        run_id="run-agent-033",
        session_id="session-agent-033",
        thread_id="thread-agent-033",
        turn=3,
        payload={"api_key": "sk-should-redact", "output_tail": "metric matched"},
        metadata={
            "tool_call_id": "call-semantic-1",
            "tool_name": "semantic_lookup",
            "result_keys": ("status", "metric_plan"),
        },
    )
    events = [
        {
            "action": "tool_result",
            "toolName": "semantic_lookup",
            "success": True,
            "metadata": {"runtime_events": [runtime_event]},
        }
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_tools=("semantic_lookup",),
            required_runtime_event_names=("tool.semantic_lookup",),
            required_runtime_event_metadata_keys={
                "tool.semantic_lookup": (
                    "tool_call_id",
                    "tool_name",
                    "result_keys",
                )
            },
            forbidden_runtime_event_metadata_keys={
                "*": ("api_key", "authorization", "raw_prompt", "resolved_secret")
            },
        ),
    )
    failures = list(verdict.failures)
    for key in (
        "event_id",
        "run_id",
        "session_id",
        "thread_id",
        "turn_id",
        "span_id",
        "timestamp",
        "kind",
        "status",
        "payload",
        "redaction",
    ):
        if runtime_event.get(key) in (None, "", [], ()):
            failures.append(f"missing-runtime-event-envelope:{key}")
    if runtime_event.get("run_id") != "run-agent-033":
        failures.append("runtime-event-run-id-not-preserved")
    if runtime_event.get("session_id") != "session-agent-033":
        failures.append("runtime-event-session-id-not-preserved")
    if runtime_event.get("turn_id") != "session-agent-033:turn:3":
        failures.append("runtime-event-turn-id-not-derived")
    if (runtime_event.get("redaction") or {}).get("policy") != (
        "runtime-event-redaction/v1"
    ):
        failures.append("runtime-event-redaction-policy-missing")
    if (runtime_event.get("payload") or {}).get("api_key") != "[redacted]":
        failures.append("runtime-event-payload-secret-not-redacted")
    passed = verdict.passed and not failures
    return {
        "id": "routing-runtime-event-replay-identity",
        "passed": passed,
        "expected_gate_passed": True,
        "actual_gate_passed": passed,
        "failures": failures,
        "verdict": verdict.as_dict(),
    }


def _runtime_event_taxonomy_gate() -> dict[str, Any]:
    runtime_events = [
        make_runtime_event(
            kind="llm",
            status="started",
            name="llm.request.started",
            session_id="session-taxonomy",
        ),
        make_runtime_event(
            kind="tool",
            status="completed",
            name="tool.semantic_lookup",
            session_id="session-taxonomy",
            metadata={"tool_call_id": "call-taxonomy-1"},
        ),
        make_runtime_event(
            kind="memory",
            status="blocked",
            name="memory.retain.blocked",
            session_id="session-taxonomy",
        ),
        make_runtime_event(
            kind="subagent",
            status="stale",
            name="subagent.delegation.timeout",
            session_id="session-taxonomy",
            metadata={"reason": "node_timeout"},
        ),
        make_runtime_event(
            kind="control",
            status="cancelled",
            name="control.session.kill",
            session_id="session-taxonomy",
            metadata={"outcome": "killed"},
        ),
    ]
    events = [
        {
            "action": "runtime_replay",
            "success": True,
            "metadata": {"runtime_events": runtime_events},
        }
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_runtime_event_names=(
                "llm.request.started",
                "tool.semantic_lookup",
                "memory.retain.blocked",
                "subagent.delegation.timeout",
                "control.session.kill",
            ),
            required_runtime_event_metadata_keys={
                "llm.request.started": ("outcome",),
                "tool.semantic_lookup": ("outcome", "tool_call_id"),
                "memory.retain.blocked": ("outcome",),
                "subagent.delegation.timeout": ("outcome",),
                "control.session.kill": ("outcome",),
            },
            required_runtime_event_metadata_values={
                "llm.request.started": {"outcome": "deferred"},
                "tool.semantic_lookup": {"outcome": "ok"},
                "memory.retain.blocked": {"outcome": "deferred"},
                "subagent.delegation.timeout": {"outcome": "timeout"},
                "control.session.kill": {"outcome": "killed"},
            },
        ),
    )
    failures = list(verdict.failures)
    for event in runtime_events:
        if not runtime_event_name_matches_kind(
            kind=event["kind"],
            name=str(event.get("name") or ""),
        ):
            failures.append(f"runtime-event-kind-name-mismatch:{event.get('name')}")
    passed = verdict.passed and not failures
    return {
        "id": "routing-runtime-event-kind-outcome-taxonomy",
        "passed": passed,
        "expected_gate_passed": True,
        "actual_gate_passed": passed,
        "failures": failures,
        "verdict": verdict.as_dict(),
    }


def _tool_hook_policy_trace_shape_gate() -> dict[str, Any]:
    events = [
        {
            "action": "tool_result",
            "toolName": "memory_search",
            "success": False,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "tool.memory_search",
                        "metadata": {
                            "tool_call_id": "call-hook-veto",
                            "tool_name": "memory_search",
                            "error_type": "tool_hook_veto",
                            "hook_policy": {
                                "hook": "pre_tool_call",
                                "decision": "veto",
                                "reason": "policy-test-veto",
                            },
                        },
                    }
                ]
            },
        },
        {
            "action": "tool_result",
            "toolName": "file_analyze",
            "success": True,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "tool.file_analyze",
                        "metadata": {
                            "tool_call_id": "call-hook-transform",
                            "tool_name": "file_analyze",
                            "result_type": "dict",
                            "hook_policy": {
                                "hook": "transform_tool_result",
                                "decision": "transformed",
                                "redacted_keys": ("secret",),
                            },
                        },
                    }
                ]
            },
        },
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            allow_tool_failures=True,
            required_runtime_event_names=(
                "tool.memory_search",
                "tool.file_analyze",
            ),
            required_runtime_event_metadata_keys={
                "tool.memory_search": (
                    "tool_call_id",
                    "tool_name",
                    "hook_policy.hook",
                    "hook_policy.decision",
                    "hook_policy.reason",
                ),
                "tool.file_analyze": (
                    "tool_call_id",
                    "tool_name",
                    "hook_policy.hook",
                    "hook_policy.decision",
                    "hook_policy.redacted_keys",
                ),
            },
            required_runtime_event_metadata_values={
                "tool.memory_search": {
                    "hook_policy.hook": "pre_tool_call",
                    "hook_policy.decision": "veto",
                },
                "tool.file_analyze": {
                    "hook_policy.hook": "transform_tool_result",
                    "hook_policy.decision": "transformed",
                    "hook_policy.redacted_keys": "secret",
                },
            },
            forbidden_runtime_event_metadata_keys={
                "*": (
                    "raw_result",
                    "raw_output",
                    "secret",
                    "api_key",
                    "authorization",
                )
            },
        ),
    )
    return _scenario_result(
        scenario_id="routing-tool-hook-policy-trace-shape",
        verdict_passed=verdict.passed,
        expected_passed=True,
        verdict=verdict,
    )


def _context_overflow_compress_retry_trace_gate() -> dict[str, Any]:
    events = [
        {
            "action": "llm_response",
            "success": True,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "llm.context_overflow_compress_retry",
                        "metadata": {
                            "runner": "langgraph",
                            "recovery_strategy": "compress",
                            "before_messages": 42,
                            "after_messages": 12,
                            "error_type": "ContextWindowExceededError",
                        },
                    }
                ],
                "degradation_flags": ("context_overflow_compress_retry",),
            },
        }
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_runtime_event_names=("llm.context_overflow_compress_retry",),
            required_runtime_event_metadata_keys={
                "llm.context_overflow_compress_retry": (
                    "runner",
                    "recovery_strategy",
                    "before_messages",
                    "after_messages",
                    "error_type",
                )
            },
            required_runtime_event_metadata_values={
                "llm.context_overflow_compress_retry": {
                    "recovery_strategy": "compress",
                }
            },
            forbidden_runtime_event_metadata_keys={
                "*": (
                    "messages",
                    "raw_prompt",
                    "raw_summary",
                    "api_key",
                    "authorization",
                )
            },
        ),
    )
    return _scenario_result(
        scenario_id="routing-context-overflow-compress-retry-trace-shape",
        verdict_passed=verdict.passed,
        expected_passed=True,
        verdict=verdict,
    )


def _subagent_isolation_runtime_gate() -> dict[str, Any]:
    child_task_id = "task-child-1"
    events = [
        {
            "action": "a2a_delegation",
            "success": True,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "subagent.delegation.accepted",
                        "metadata": {
                            "child_task_id": child_task_id,
                            "context_mode": "isolated",
                            "memory_write_policy": "parent_only",
                            "allowed_tools": ("semantic_lookup",),
                            "spawn_depth": 1,
                        },
                    },
                    {
                        "name": "subagent.delegation.started",
                        "metadata": {
                            "child_task_id": child_task_id,
                            "context_mode": "isolated",
                        },
                    },
                    {
                        "name": "subagent.delegation.completed",
                        "metadata": {
                            "child_task_id": child_task_id,
                            "status": "completed",
                        },
                    },
                    {
                        "name": "subagent.parent_memory_handoff",
                        "metadata": {
                            "child_task_id": child_task_id,
                            "child_memory_write_allowed": False,
                            "output_digest": "sha256:child-output",
                        },
                    },
                ]
            },
        },
        {
            "action": "memory_retain",
            "success": False,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "memory.retain.blocked",
                        "metadata": {
                            "thread_id": "a2a-child-1",
                            "reason": "child_memory_write_disabled",
                            "memory_write_policy": "parent_only",
                        },
                    }
                ]
            },
        },
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_runtime_event_names=(
                "subagent.delegation.accepted",
                "subagent.delegation.started",
                "subagent.delegation.completed",
                "subagent.parent_memory_handoff",
                "memory.retain.blocked",
            ),
            required_runtime_event_metadata_keys={
                "subagent.delegation.accepted": (
                    "child_task_id",
                    "context_mode",
                    "memory_write_policy",
                    "allowed_tools",
                    "spawn_depth",
                ),
                "subagent.parent_memory_handoff": (
                    "child_task_id",
                    "child_memory_write_allowed",
                    "output_digest",
                ),
                "memory.retain.blocked": (
                    "thread_id",
                    "reason",
                    "memory_write_policy",
                ),
            },
            forbidden_runtime_event_metadata_keys={
                "*": (
                    "raw_output",
                    "messages",
                    "parent_history",
                    "api_key",
                    "authorization",
                )
            },
            required_runtime_event_metadata_values={
                "subagent.delegation.accepted": {
                    "context_mode": "isolated",
                    "memory_write_policy": "parent_only",
                    "allowed_tools": "semantic_lookup",
                },
                "subagent.parent_memory_handoff": {
                    "child_memory_write_allowed": "false"
                },
                "memory.retain.blocked": {
                    "reason": "child_memory_write_disabled",
                    "memory_write_policy": "parent_only",
                },
            },
            forbidden_runtime_event_metadata_values={
                "subagent.delegation.accepted": {"allowed_tools": "memory_add"}
            },
        ),
    )
    return _scenario_result(
        scenario_id="routing-subagent-isolation-runtime",
        verdict_passed=verdict.passed,
        expected_passed=True,
        verdict=verdict,
    )


def _subagent_forged_child_tools_filtered_gate() -> dict[str, Any]:
    child_task_id = "task-child-forged-tools"
    tool_policy = build_child_tool_policy(
        requested_tools=(
            "semantic_lookup",
            "memory_add",
            "delegate_task",
            "send_message",
        )
    )
    events = [
        {
            "action": "a2a_child_policy",
            "success": True,
            "metadata": {
                "runtime_events": [
                    {
                        "name": "subagent.delegation.accepted",
                        "metadata": {
                            "child_task_id": child_task_id,
                            "context_mode": "isolated",
                            "memory_write_policy": tool_policy["memory_write_policy"],
                            "allowed_tools": tuple(tool_policy["allowed_tools"]),
                            "blocked_tools": tuple(tool_policy["blocked_tools"]),
                            "approval_mode": tool_policy["approval_mode"],
                            "recursive_delegation_allowed": tool_policy[
                                "recursive_delegation_allowed"
                            ],
                            "cross_platform_send_allowed": tool_policy[
                                "cross_platform_send_allowed"
                            ],
                        },
                    }
                ]
            },
        }
    ]
    verdict = evaluate_trace_gates(
        events,
        TraceExpectations(
            required_runtime_event_names=("subagent.delegation.accepted",),
            required_runtime_event_metadata_keys={
                "subagent.delegation.accepted": (
                    "allowed_tools",
                    "blocked_tools",
                    "memory_write_policy",
                    "approval_mode",
                    "recursive_delegation_allowed",
                    "cross_platform_send_allowed",
                )
            },
            required_runtime_event_metadata_values={
                "subagent.delegation.accepted": {
                    "allowed_tools": "semantic_lookup",
                    "blocked_tools": "memory_add",
                    "memory_write_policy": "parent_only",
                    "approval_mode": "non_interactive_auto_deny",
                    "recursive_delegation_allowed": "false",
                    "cross_platform_send_allowed": "false",
                }
            },
            forbidden_runtime_event_metadata_values={
                "subagent.delegation.accepted": {
                    "allowed_tools": "memory_add",
                }
            },
        ),
    )
    failures = list(verdict.failures)
    if tool_policy["allowed_tools"] != ["semantic_lookup"]:
        failures.append("forged-child-tools-not-filtered")
    for forbidden_tool in ("memory_add", "delegate_task", "send_message"):
        if forbidden_tool not in tool_policy["blocked_tools"]:
            failures.append(f"forged-child-tool-not-blocked:{forbidden_tool}")
    passed = verdict.passed and not failures
    return {
        "id": "routing-subagent-forged-child-tools-filtered",
        "passed": passed,
        "expected_gate_passed": True,
        "actual_gate_passed": passed,
        "failures": failures,
        "verdict": verdict.as_dict(),
    }


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
