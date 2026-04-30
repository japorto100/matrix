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
