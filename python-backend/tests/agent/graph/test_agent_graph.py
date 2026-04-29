from __future__ import annotations

from agent.graph.agent_graph import _route_after_tools, create_agent_graph


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
