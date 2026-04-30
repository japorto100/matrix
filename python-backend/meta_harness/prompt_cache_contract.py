"""Provider-free Meta-Harness lane for Feature 032 prompt-cache telemetry."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent.llm.request_telemetry import build_request_telemetry

DEFAULT_RUN_ID = "run-prompt-cache-contract"


def run_prompt_cache_contract_scenarios(
    *,
    run_id: str = DEFAULT_RUN_ID,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run deterministic prompt/tool digest and usage telemetry scenarios."""

    data_root = data_dir or Path(__file__).resolve().parents[2] / "data" / "meta_harness"
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        _stable_prompt_and_tool_order_gate(),
        _prompt_content_change_gate(),
        _tool_schema_change_gate(),
        _cache_snapshot_break_dimension_gate(),
        _mcp_reload_cache_impact_gate(),
        _thread_rollup_gate(),
        _durable_aggregate_gate(),
        _usage_unknown_counter_gate(),
    ]
    passed = all(scenario["passed"] for scenario in scenarios)
    summary = {
        "run_id": run_id,
        "kind": "prompt_cache_contract",
        "feature_id": "032",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "scenario_count": len(scenarios),
        "passed_count": sum(1 for scenario in scenarios if scenario["passed"]),
        "scenarios": scenarios,
    }
    _write_json(run_dir / "prompt_cache_contract.json", summary)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "kind": "prompt_cache_contract",
            "feature_id": "032",
            "frontend_required": False,
            "provider_calls_required": False,
            "created_at": summary["created_at"],
        },
    )
    return {**summary, "artifact_path": str(run_dir / "prompt_cache_contract.json")}


def _stable_prompt_and_tool_order_gate() -> dict[str, Any]:
    messages = [{"role": "user", "content": "Summarize portfolio risk."}]
    first = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="langgraph",
        thread_id="thread-cache",
        iteration=0,
        messages=messages,
        tools=[_tool("memory_search"), _tool("semantic_lookup")],
        usage={"prompt_tokens": 10, "completion_tokens": 3},
    )
    second = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="langgraph",
        thread_id="thread-cache",
        iteration=1,
        messages=messages,
        tools=[_tool("semantic_lookup"), _tool("memory_search")],
        usage={"prompt_tokens": 10, "completion_tokens": 3},
        previous=first,
    )
    failures: list[str] = []
    if first["prompt_digest"] != second["prompt_digest"]:
        failures.append("prompt_digest changed for equivalent prompt")
    if first["prompt_layout_digest"] != second["prompt_layout_digest"]:
        failures.append("prompt_layout_digest changed for equivalent prompt")
    if first["tool_catalog_digest"] != second["tool_catalog_digest"]:
        failures.append("tool_catalog_digest changed for reordered tools")
    if second["cache_break_reasons"]:
        failures.append(f"unexpected cache break: {second['cache_break_reasons']}")
    return _scenario(
        "prompt-cache-stable-prompt-tool-order",
        failures=failures,
        evidence={
            "prompt_digest": second["prompt_digest"],
            "prompt_layout_digest": second["prompt_layout_digest"],
            "tool_catalog_digest": second["tool_catalog_digest"],
        },
    )


def _prompt_content_change_gate() -> dict[str, Any]:
    first = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="simple",
        thread_id="thread-cache",
        iteration=0,
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        usage={"prompt_tokens": 2, "completion_tokens": 1},
    )
    second = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="simple",
        thread_id="thread-cache",
        iteration=1,
        messages=[{"role": "user", "content": "world"}],
        tools=[],
        usage={"prompt_tokens": 2, "completion_tokens": 1},
        previous=first,
    )
    reasons = set(second["cache_break_reasons"])
    failures = []
    if "prompt_content_changed" not in reasons:
        failures.append("missing prompt_content_changed")
    if "prompt_layout_changed" in reasons:
        failures.append("content-only change should not be layout churn")
    return _scenario(
        "prompt-cache-content-change-reason",
        failures=failures,
        evidence={"cache_break_reasons": second["cache_break_reasons"]},
    )


def _tool_schema_change_gate() -> dict[str, Any]:
    first = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="langgraph",
        thread_id="thread-cache",
        iteration=0,
        messages=[{"role": "user", "content": "search memory"}],
        tools=[_tool("memory_search")],
        usage={"prompt_tokens": 5, "completion_tokens": 2},
    )
    changed_tool = _tool(
        "memory_search",
        description="Search memory with stricter filters",
        schema={"type": "object", "properties": {"query": {"type": "string"}}},
    )
    second = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="langgraph",
        thread_id="thread-cache",
        iteration=1,
        messages=[{"role": "user", "content": "search memory"}],
        tools=[changed_tool],
        usage={"prompt_tokens": 5, "completion_tokens": 2},
        previous=first,
    )
    failures = []
    if "tool_catalog_changed" not in set(second["cache_break_reasons"]):
        failures.append("missing tool_catalog_changed")
    return _scenario(
        "prompt-cache-tool-schema-change-reason",
        failures=failures,
        evidence={"cache_break_reasons": second["cache_break_reasons"]},
    )


def _cache_snapshot_break_dimension_gate() -> dict[str, Any]:
    first = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="langgraph",
        transport="litellm_chat_completions",
        cache_retention="ephemeral_breakpoints",
        stream_strategy="non_streaming",
        thread_id="thread-cache",
        iteration=0,
        messages=[{"role": "system", "content": "policy"}, {"role": "user", "content": "go"}],
        tools=[_tool("memory_search"), _tool("semantic_lookup")],
        usage={"prompt_tokens": 5, "completion_tokens": 2},
    )
    second = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="langgraph",
        transport="responses",
        cache_retention="provider_default",
        stream_strategy="sse",
        thread_id="thread-cache",
        iteration=1,
        messages=[{"role": "system", "content": "new policy"}, {"role": "user", "content": "go"}],
        tools=[_tool("memory_search"), _tool("semantic_lookup")],
        usage={"prompt_tokens": 5, "completion_tokens": 2},
        previous=first,
    )
    reasons = set(second["cache_break_reasons"])
    failures: list[str] = []
    for reason in (
        "transport_changed",
        "cache_retention_changed",
        "stream_strategy_changed",
        "system_prompt_changed",
    ):
        if reason not in reasons:
            failures.append(f"missing {reason}")
    if second.get("tool_count") != 2:
        failures.append("missing tool_count snapshot")
    if second.get("tool_names") != ("memory_search", "semantic_lookup"):
        failures.append("tool_names snapshot not sorted")
    if len(str(second.get("system_prompt_digest") or "")) != 64:
        failures.append("missing system_prompt_digest")
    return _scenario(
        "prompt-cache-snapshot-break-dimensions",
        failures=failures,
        evidence={
            "cache_break_reasons": second["cache_break_reasons"],
            "transport": second.get("transport"),
            "cache_retention": second.get("cache_retention"),
            "stream_strategy": second.get("stream_strategy"),
            "tool_count": second.get("tool_count"),
            "tool_names": second.get("tool_names"),
        },
    )


def _usage_unknown_counter_gate() -> dict[str, Any]:
    telemetry = build_request_telemetry(
        provider="provider",
        model="model-a",
        router="simple",
        thread_id="thread-cache",
        iteration=0,
        messages=[{"role": "user", "content": "usage check"}],
        tools=[],
        usage={"prompt_tokens": 8, "completion_tokens": 2},
    )
    usage = telemetry["usage"]
    failures = []
    if usage.get("prompt_tokens") != 8 or usage.get("output_tokens") != 2:
        failures.append("missing normalized prompt/output counters")
    unknown = set(usage.get("unknown_fields") or ())
    for key in ("input_tokens", "cache_read_tokens", "cache_write_tokens"):
        if key not in unknown:
            failures.append(f"missing unknown marker: {key}")
    return _scenario(
        "prompt-cache-usage-unknown-counters",
        failures=failures,
        evidence={"usage": usage},
    )


def _mcp_reload_cache_impact_gate() -> dict[str, Any]:
    from agent.control.cache_impact import (
        build_cache_impact,
        cache_impact_runtime_event,
        digest_records,
    )
    from agent.control.prompt_cache import build_prompt_cache_read_model

    previous_digest = digest_records([{"name": "memory_search", "schema": "v1"}])
    next_digest = digest_records(
        [
            {"name": "memory_search", "schema": "v1"},
            {"name": "semantic_lookup", "schema": "v1"},
        ]
    )
    impact = build_cache_impact(
        source="mcp_reload",
        reason="tool_catalog_changed",
        previous_digest=previous_digest,
        next_digest=next_digest,
        scope={"thread_id": "thread-cache"},
        details={"tool_count": 2},
    )
    runtime_event = cache_impact_runtime_event(
        impact,
        session_id="session-cache",
        thread_id="thread-cache",
    )
    read_model = build_prompt_cache_read_model(
        audit_events=[
            {
                "id": "audit-cache-impact-1",
                "timestamp": datetime.now(UTC).isoformat(),
                "thread_id": "thread-cache",
                "metadata": {"runtime_events": [runtime_event]},
            }
        ]
    )
    failures: list[str] = []
    if impact.get("action") != "rebind_required":
        failures.append("cache-impact-not-rebind-required")
    if runtime_event.get("name") != "cache.invalidated":
        failures.append("cache-impact-runtime-event-not-invalidated")
    if read_model["summary"]["cache_invalidations"] != 1:
        failures.append("prompt-cache-read-model-missing-invalidation")
    if not read_model["cache_impacts"]:
        failures.append("prompt-cache-read-model-missing-impact")
    else:
        replayed = read_model["cache_impacts"][0]
        if replayed.get("source") != "mcp_reload":
            failures.append("prompt-cache-impact-source-not-replayed")
        if replayed.get("reason") != "tool_catalog_changed":
            failures.append("prompt-cache-impact-reason-not-replayed")
    return _scenario(
        "prompt-cache-mcp-reload-impact-replayed",
        failures=failures,
        evidence={
            "impact": impact,
            "runtime_event_name": runtime_event.get("name"),
            "read_model_summary": read_model.get("summary"),
        },
    )


def _thread_rollup_gate() -> dict[str, Any]:
    from agent.control.prompt_cache import build_prompt_cache_read_model

    read_model = build_prompt_cache_read_model(
        audit_events=[
            {
                "id": "audit-cache-thread-1",
                "timestamp": datetime.now(UTC).isoformat(),
                "thread_id": "thread-cache",
                "metadata": {
                    "request_telemetry": [
                        {
                            "provider": "provider-a",
                            "model": "model-a",
                            "router": "langgraph",
                            "thread_id": "thread-cache",
                            "iteration": 1,
                            "prompt_digest": "prompt-a",
                            "prompt_layout_digest": "layout-a",
                            "tool_catalog_digest": "tools-a",
                            "cache_break_reasons": ["first_request"],
                            "usage": {
                                "prompt_tokens": 100,
                                "completion_tokens": 20,
                                "total_tokens": 120,
                                "cache_read_tokens": 40,
                                "cache_write_tokens": 10,
                                "unknown_fields": [],
                            },
                        },
                        {
                            "provider": "provider-a",
                            "model": "model-a",
                            "router": "langgraph",
                            "thread_id": "thread-cache",
                            "iteration": 2,
                            "prompt_digest": "prompt-b",
                            "prompt_layout_digest": "layout-a",
                            "tool_catalog_digest": "tools-a",
                            "cache_break_reasons": ["prompt_content_changed"],
                            "usage": {
                                "prompt_tokens": 80,
                                "completion_tokens": 10,
                                "total_tokens": 90,
                                "cache_read_tokens": 55,
                                "cache_write_tokens": 0,
                                "unknown_fields": ["reasoning_tokens"],
                            },
                        },
                    ]
                },
            }
        ]
    )
    summary = read_model.get("by_thread", {}).get("thread-cache", {})
    failures: list[str] = []
    if summary.get("requests") != 2:
        failures.append("thread-rollup-request-count")
    if summary.get("cache_read_tokens") != 95:
        failures.append("thread-rollup-cache-read")
    if summary.get("cache_write_tokens") != 10:
        failures.append("thread-rollup-cache-write")
    if summary.get("cache_breaks") != 2:
        failures.append("thread-rollup-cache-breaks")
    if summary.get("providers") != ["provider-a"]:
        failures.append("thread-rollup-provider-dedupe")
    return _scenario(
        "prompt-cache-thread-session-rollup",
        failures=failures,
        evidence={"thread_summary": summary},
    )


def _durable_aggregate_gate() -> dict[str, Any]:
    from agent.control.prompt_cache import (
        build_prompt_cache_aggregate_model,
        build_prompt_cache_read_model,
    )

    read_model = build_prompt_cache_read_model(
        audit_events=[
            {
                "id": "audit-cache-aggregate-1",
                "timestamp": "2026-04-30T10:00:00+00:00",
                "thread_id": "thread-a",
                "metadata": {
                    "request_telemetry": {
                        "provider": "provider-a",
                        "model": "model-a",
                        "thread_id": "thread-a",
                        "cache_break_reasons": ["first_request"],
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 10,
                            "total_tokens": 110,
                            "cache_read_tokens": 70,
                            "cache_write_tokens": 5,
                            "unknown_fields": [],
                        },
                    }
                },
            },
            {
                "id": "audit-cache-aggregate-2",
                "timestamp": "2026-04-30T10:05:00+00:00",
                "thread_id": "thread-b",
                "metadata": {
                    "request_telemetry": {
                        "provider": "provider-a",
                        "model": "model-b",
                        "thread_id": "thread-b",
                        "cache_break_reasons": [],
                        "usage": {
                            "prompt_tokens": 40,
                            "completion_tokens": 4,
                            "total_tokens": 44,
                            "cache_read_tokens": 20,
                            "cache_write_tokens": 0,
                            "unknown_fields": ["reasoning_tokens"],
                        },
                    }
                },
            },
        ],
        limit=2,
    )
    aggregate = build_prompt_cache_aggregate_model(read_model, user_id="user-cache")
    summary = aggregate.get("summary", {})
    failures: list[str] = []
    if aggregate.get("contract") != "prompt-cache-aggregate/v1":
        failures.append("aggregate-contract-missing")
    if summary.get("threads") != 2:
        failures.append("aggregate-thread-count")
    if summary.get("requests") != 2:
        failures.append("aggregate-request-count")
    if summary.get("cache_read_tokens") != 90:
        failures.append("aggregate-cache-read")
    if set(summary.get("models") or []) != {"model-a", "model-b"}:
        failures.append("aggregate-model-dedupe")
    return _scenario(
        "prompt-cache-durable-aggregate-rollup",
        failures=failures,
        evidence={"aggregate_summary": summary},
    )


def _tool(
    name: str,
    *,
    description: str = "Tool summary",
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema or {"type": "object"},
        },
    }


def _scenario(
    scenario_id: str,
    *,
    failures: list[str],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": scenario_id,
        "passed": not failures,
        "failures": failures,
        "evidence": evidence,
    }


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
