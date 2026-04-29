from __future__ import annotations

from agent.graph.orchestrator import _aggregate_analyses, create_orchestrator_graph


def test_create_orchestrator_graph_compiles_all_trading_roles():
    graph = create_orchestrator_graph()

    assert {
        "__start__",
        "fundamentals",
        "sentiment",
        "technical",
        "aggregate",
        "researcher",
        "trader",
        "risk_manager",
        "tools",
        "__end__",
    } <= set(graph.get_graph().nodes)


async def test_aggregate_analyses_summarizes_recent_assistant_messages():
    result = await _aggregate_analyses(
        {
            "messages": [
                {"role": "assistant", "content": "fundamental view"},
                {"role": "tool", "content": "ignored"},
                {"role": "assistant", "content": "technical view"},
            ]
        }
    )

    content = result["messages"][0]["content"]
    assert "fundamental view" in content
    assert "technical view" in content
    assert "ignored" not in content
