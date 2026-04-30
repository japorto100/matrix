from __future__ import annotations

from agent.routing.delegation_policy import (
    build_child_tool_policy,
    build_delegation_defer_metadata,
    build_route_decision_metadata,
    build_single_hop_delegation_policy,
    route_taxonomy_for_tools,
)


def test_route_taxonomy_keeps_no_tool_turn_direct() -> None:
    assert route_taxonomy_for_tools([]) == "direct_answer"


def test_route_taxonomy_marks_retrieval_before_future_delegation() -> None:
    assert route_taxonomy_for_tools(["memory_search"]) == "retrieval_answer"
    assert route_taxonomy_for_tools(["kg_search"]) == "retrieval_answer"
    assert route_taxonomy_for_tools(["semantic_lookup"]) == "retrieval_answer"


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


def test_delegation_defer_metadata_never_spawns() -> None:
    metadata = build_delegation_defer_metadata(
        runner="dispatcher",
        delegate_kind="domain",
        requested_reason="needs_risk_delegate",
        max_spawn_depth=1,
    )

    assert metadata["decision"] == "defer"
    assert metadata["route_taxonomy"] == "subagent_deferred"
    assert metadata["delegation_decision"] == "deferred"
    assert metadata["delegate_kind"] == "domain"
    assert metadata["spawn_depth"] == 0
    assert metadata["max_spawn_depth"] == 1
    assert metadata["fallback_reason"] == "subagents_disabled"


def test_child_tool_policy_blocks_recursive_memory_and_send_tools() -> None:
    policy = build_child_tool_policy(
        requested_tools=[
            "semantic_lookup",
            "delegate_task",
            "memory_add",
            "send_message",
        ]
    )

    assert policy["allowed_tools"] == ["semantic_lookup"]
    assert policy["blocked_tools"] == ["delegate_task", "memory_add", "send_message"]
    assert policy["memory_write_policy"] == "parent_only"
    assert policy["approval_mode"] == "non_interactive_auto_deny"
    assert policy["recursive_delegation_allowed"] is False
    assert policy["cross_platform_send_allowed"] is False


def test_single_hop_delegation_policy_is_fail_closed_by_depth() -> None:
    blocked = build_single_hop_delegation_policy(
        runner="langgraph",
        role="researcher",
        current_depth=0,
        max_spawn_depth=0,
        requested_tools=["semantic_lookup"],
    )
    accepted = build_single_hop_delegation_policy(
        runner="langgraph",
        role="researcher",
        current_depth=0,
        max_spawn_depth=1,
        requested_tools=["semantic_lookup"],
    )

    assert blocked["delegation_decision"] == "blocked"
    assert blocked["fallback_reason"] == "spawn_depth_exceeded"
    assert accepted["delegation_decision"] == "accepted"
    assert accepted["next_spawn_depth"] == 1
    assert accepted["tool_policy"]["allowed_tools"] == ["semantic_lookup"]
