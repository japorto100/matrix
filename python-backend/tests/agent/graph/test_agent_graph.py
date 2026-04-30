from __future__ import annotations

import pytest

from agent.graph.agent_graph import (
    _increment_iteration,
    _route_after_tools,
    create_agent_graph,
)


def test_create_agent_graph_compiles_with_default_memory_saver(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_DB_URL", "postgresql://unused/should-not-break-compile")

    graph = create_agent_graph()

    assert {
        "__start__",
        "memory_recall",
        "router",
        "llm_call",
        "approval_gate",
        "tool_execute",
        "increment",
        "memory_retain",
        "__end__",
    } <= set(graph.get_graph().nodes)


def test_route_after_tools_respects_state_max_iterations():
    assert _route_after_tools({"iteration": 0, "max_iterations": 2}) == "llm"
    assert _route_after_tools({"iteration": 1, "max_iterations": 2}) == "retain"


def test_route_after_tools_stops_when_loop_guard_marks_done():
    assert (
        _route_after_tools({"done": True, "iteration": 0, "max_iterations": 10})
        == "retain"
    )


@pytest.mark.asyncio
async def test_increment_iteration_stops_repeated_tool_failures(monkeypatch):
    class _Limiter:
        def record_iteration(self, thread_id):
            return None

    monkeypatch.setenv("AGENT_MAX_TOOL_FAILURES_PER_TOOL", "2")
    monkeypatch.setattr(
        "agent.consent.rate_limiter.get_rate_limiter",
        lambda: _Limiter(),
    )

    update = await _increment_iteration(
        {
            "thread_id": "t-loop",
            "iteration": 1,
            "degradation_flags": [],
            "tool_results": [
                {
                    "tool_call_id": "call-1",
                    "tool_name": "kg_search",
                    "result": {},
                    "error": "boom",
                },
                {
                    "tool_call_id": "call-2",
                    "tool_name": "kg_search",
                    "result": {},
                    "error": "boom again",
                },
            ],
        }
    )

    assert update["iteration"] == 2
    assert update["done"] is True
    assert update["loop_guard"]["tool_name"] == "kg_search"
    assert "tool_retry_guard_stopped" in update["degradation_flags"]
