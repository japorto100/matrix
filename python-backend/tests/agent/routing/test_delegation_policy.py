from __future__ import annotations

from agent.routing.delegation_policy import (
    build_route_decision_metadata,
    route_taxonomy_for_tools,
)


def test_route_taxonomy_keeps_no_tool_turn_direct() -> None:
    assert route_taxonomy_for_tools([]) == "direct_answer"


def test_route_taxonomy_marks_retrieval_before_future_delegation() -> None:
    assert route_taxonomy_for_tools(["memory_search"]) == "retrieval_answer"
    assert route_taxonomy_for_tools(["kg_search"]) == "retrieval_answer"


def test_route_decision_metadata_disables_delegation_by_default() -> None:
    metadata = build_route_decision_metadata(
        runner="simple",
        tool_names=["memory_search"],
        routing_reason="simple_turn",
        routing_used=True,
        routing_picked_model="openrouter/test-model",
    )

    assert metadata["decision"] == "tool_use"
    assert metadata["route_taxonomy"] == "retrieval_answer"
    assert metadata["delegation_decision"] == "none"
    assert metadata["delegate_kind"] is None
    assert metadata["spawn_depth"] == 0
    assert metadata["max_spawn_depth"] == 0
    assert metadata["fallback_reason"] == "subagents_disabled"
    assert metadata["allowed_tools"] == ["memory_search"]
    assert metadata["memory_scope"] == "current_user"
    assert metadata["memory_route_requested"] is True
    assert metadata["retrieval_route_requested"] is True
