from __future__ import annotations

from typing import Any

import pytest

from agent.consent.rate_limiter import SessionRateLimiter
from agent.context import AgentExecutionContext
from agent.graph.nodes import tool_node as tool_node_module
from agent.graph.nodes.tool_node import (
    TOOL_LLM_OUTPUT_MAX_CHARS,
    _cap_tool_llm_content,
    _effective_tool_timeout,
    _execute_single,
    _trading_role_from_state,
    tool_node,
)
from agent.roles import TradingRole
from agent.tools.base import TradingTool
from agent.tools.registry import ToolRegistry


class _StubTool(TradingTool):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def definition(self) -> dict[str, Any]:
        return {"name": self._name, "description": "", "input_schema": {"type": "object"}}

    async def execute(self, tool_input: dict[str, Any], ctx: Any) -> dict[str, Any]:
        return {"ok": True}


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(_StubTool("get_portfolio_summary"))
    registry.register(_StubTool("set_chart_state"))
    return registry


def test_trading_role_from_state_accepts_known_roles_only():
    assert _trading_role_from_state({"current_role": "risk_manager"}) is TradingRole.RISK_MANAGER
    assert _trading_role_from_state({"current_role": "default"}) is None
    assert _trading_role_from_state({}) is None


def test_memory_tools_get_extended_timeout_budget():
    assert _effective_tool_timeout("memory_add") == tool_node_module.MEMORY_TOOL_TIMEOUT_SEC
    assert _effective_tool_timeout("memory_search") == tool_node_module.MEMORY_TOOL_TIMEOUT_SEC
    assert _effective_tool_timeout("get_chart_state") == tool_node_module.TOOL_TIMEOUT_SEC


def test_cap_tool_llm_content_is_idempotent_and_keeps_marker():
    content = "x" * (TOOL_LLM_OUTPUT_MAX_CHARS + 100)

    capped = _cap_tool_llm_content("get_portfolio_summary", content)
    recapped = _cap_tool_llm_content("get_portfolio_summary", capped)

    assert len(capped) < len(content)
    assert "[tool_output_truncated" in capped
    assert f"original_chars={len(content)}" in capped
    assert recapped == capped


@pytest.mark.asyncio
async def test_tool_node_filters_registry_for_current_trading_role(monkeypatch):
    seen: list[tuple[str, bool]] = []

    async def fake_execute_single(tc, registry, ctx):
        seen.append((tc["tool_name"], registry.lookup(tc["tool_name"]) is not None))
        return {
            "tool_call_id": tc["tool_call_id"],
            "tool_name": tc["tool_name"],
            "result": {},
            "error": "blocked for test",
        }

    class _Limiter:
        def record_tool_call(self, thread_id: str, tool_name: str) -> None:
            return None

    monkeypatch.setattr(tool_node_module.ToolRegistry, "load", classmethod(lambda cls: _registry()))
    monkeypatch.setattr(tool_node_module, "_execute_single", fake_execute_single)
    monkeypatch.setattr(
        "agent.consent.rate_limiter.get_rate_limiter",
        lambda: _Limiter(),
    )

    await tool_node(
        {
            "tool_calls": [
                {"tool_call_id": "1", "tool_name": "get_portfolio_summary", "tool_input": {}},
                {"tool_call_id": "2", "tool_name": "set_chart_state", "tool_input": {}},
            ],
            "current_role": "risk_manager",
            "user_id": "alice",
            "thread_id": "t1",
            "model": "test-model",
            "reasoning_effort": None,
        }
    )

    assert seen == [
        ("get_portfolio_summary", True),
        ("set_chart_state", False),
    ]


@pytest.mark.asyncio
async def test_tool_node_emits_openai_compatible_tool_call_id(monkeypatch):
    async def fake_execute_single(tc, registry, ctx):
        return {
            "tool_call_id": tc["tool_call_id"],
            "tool_name": tc["tool_name"],
            "result": {"ok": True},
            "error": None,
        }

    class _Limiter:
        def record_tool_call(self, thread_id: str, tool_name: str) -> None:
            return None

    monkeypatch.setattr(tool_node_module.ToolRegistry, "load", classmethod(lambda cls: _registry()))
    monkeypatch.setattr(tool_node_module, "_execute_single", fake_execute_single)
    monkeypatch.setattr(
        "agent.consent.rate_limiter.get_rate_limiter",
        lambda: _Limiter(),
    )

    result = await tool_node(
        {
            "tool_calls": [
                {
                    "tool_call_id": "call_123",
                    "tool_name": "get_portfolio_summary",
                    "tool_input": {},
                },
            ],
            "current_role": None,
            "user_id": "alice",
            "thread_id": "t1",
            "model": "test-model",
            "reasoning_effort": None,
        }
    )

    assert result["messages"][0]["role"] == "tool"
    assert result["messages"][0]["tool_call_id"] == "call_123"
    assert result["messages"][0]["tool_use_id"] == "call_123"
    assert '{"ok": true}' in result["messages"][0]["content"]
    assert result["runtime_events"][0]["kind"] == "tool"
    assert result["runtime_events"][0]["status"] == "completed"
    assert result["runtime_events"][0]["metadata"]["tool_call_id"] == "call_123"


@pytest.mark.asyncio
async def test_tool_node_caps_large_sanitized_tool_message(monkeypatch):
    large_payload = "x" * (TOOL_LLM_OUTPUT_MAX_CHARS + 5000)

    async def fake_execute_single(tc, registry, ctx):
        return {
            "tool_call_id": tc["tool_call_id"],
            "tool_name": tc["tool_name"],
            "result": {"payload": large_payload},
            "error": None,
        }

    class _Limiter:
        def record_tool_call(self, thread_id: str, tool_name: str) -> None:
            return None

    monkeypatch.setattr(tool_node_module.ToolRegistry, "load", classmethod(lambda cls: _registry()))
    monkeypatch.setattr(tool_node_module, "_execute_single", fake_execute_single)
    monkeypatch.setattr(
        "agent.consent.rate_limiter.get_rate_limiter",
        lambda: _Limiter(),
    )

    result = await tool_node(
        {
            "tool_calls": [
                {
                    "tool_call_id": "call_large",
                    "tool_name": "get_portfolio_summary",
                    "tool_input": {},
                },
            ],
            "current_role": None,
            "user_id": "alice",
            "thread_id": "t1",
            "model": "test-model",
            "reasoning_effort": None,
        }
    )

    message = result["messages"][0]
    assert "[tool_output_truncated" in message["content"]
    assert len(message["content"]) < len(large_payload)
    assert result["tool_results"][0]["result"]["payload"] == large_payload


@pytest.mark.asyncio
async def test_execute_single_audits_tool_budget_metadata(monkeypatch):
    captured: list[dict[str, Any]] = []
    limiter = SessionRateLimiter()
    limiter.record_tool_call("t-budget", "get_portfolio_summary")
    limiter.record_tokens("t-budget", 123)
    limiter.record_iteration("t-budget")

    async def fake_audit_log(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr("agent.audit.logger.audit_log", fake_audit_log)
    monkeypatch.setattr("agent.consent.rate_limiter.get_rate_limiter", lambda: limiter)

    ctx = AgentExecutionContext(
        user_id="alice",
        thread_id="t-budget",
        model="test-model",
        system_prompt="",
        tools=(),
    )

    result = await _execute_single(
        {
            "tool_call_id": "call_budget",
            "tool_name": "get_portfolio_summary",
            "tool_input": {},
        },
        _registry(),
        ctx,
    )

    assert result["error"] is None
    result_event = captured[-1]
    assert result_event["metadata"]["tool_calls_total_before"] == 1
    assert result_event["metadata"]["tool_calls_for_tool_before"] == 1
    assert result_event["metadata"]["tokens_used"] == 123
    assert result_event["metadata"]["iterations_used"] == 1
    assert result_event["metadata"]["iterations_limit"] > 0
    runtime_event = result_event["metadata"]["runtime_events"][0]
    assert runtime_event["kind"] == "tool"
    assert runtime_event["status"] == "completed"
    assert runtime_event["metadata"]["tool_call_id"] == "call_budget"
    assert runtime_event["metadata"]["result_keys"] == ["ok"]
