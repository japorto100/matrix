from __future__ import annotations

from typing import Any

import pytest

from agent.graph.nodes import tool_node as tool_node_module
from agent.graph.nodes.tool_node import (
    _effective_tool_timeout,
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
