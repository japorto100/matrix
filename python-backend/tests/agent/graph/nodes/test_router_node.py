"""Tests for agent/graph/nodes/router_node.py — ADR-001 P1.

router_node replaces the smart-routing inline block in llm_node.py.
It produces the routing decision as first-class state updates so
llm_node becomes consumer-only.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent.graph.nodes.router_node import router_node


def _state(**overrides):
    base = {
        "messages": [{"role": "user", "content": "hi"}],
        "tool_calls": [],
        "tool_results": [],
        "iteration": 0,
        "max_iterations": 10,
        "current_role": "default",
        "system_prompt": "sys",
        "model": "claude-opus-4-7",
        "api_key": None,
        "reasoning_effort": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cached_tokens": 0,
        "token_usage": 0,
        "llm_provider": "",
        "llm_model": "claude-opus-4-7",
        "source_layer_counts": {},
        "context_blocks": [],
        "degradation_flags": [],
        "final_response": "",
        "done": False,
        "thread_id": "t-1",
        "user_id": "alice",
        "agent_class": "advisory",
        "user_role": "viewer",
        "ab_row_id": "",
        "routing_reason": "not_evaluated",
        "routing_used": False,
        "routing_picked_model": "",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_anonymous_user_skips_routing():
    """Anonymous traffic has no user config — short-circuit to primary."""
    out = await router_node(_state(user_id="anonymous"))
    assert out["model"] == "claude-opus-4-7"
    assert out["routing_reason"] == "not_evaluated"
    assert out["routing_used"] is False


@pytest.mark.asyncio
async def test_no_config_stays_primary():
    """User with no smart_routing config falls through cleanly."""
    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(return_value=None),
    ):
        out = await router_node(_state())
    assert out["model"] == "claude-opus-4-7"
    assert out["routing_reason"] == "config_absent"
    assert out["routing_used"] is False
    assert out["routing_picked_model"] == "claude-opus-4-7"


@pytest.mark.asyncio
async def test_simple_message_with_credentials_routes_to_cheap():
    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(return_value={"enabled": True, "cheap_model": "openai/gpt-4o-mini"}),
    ), patch(
        "agent.security.credentials.user_has_provider_credential",
        AsyncMock(return_value=True),
    ):
        out = await router_node(_state())

    assert out["model"] == "openai/gpt-4o-mini"
    assert out["llm_model"] == "openai/gpt-4o-mini"
    assert out["routing_used"] is True
    assert out["routing_reason"] == "simple_turn"
    assert out["routing_picked_model"] == "openai/gpt-4o-mini"


@pytest.mark.asyncio
async def test_cross_provider_without_credentials_keeps_primary():
    """ADR-001 G2: no Anthropic-only user should silently switch to OpenAI."""
    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(return_value={"enabled": True, "cheap_model": "openai/gpt-4o-mini"}),
    ), patch(
        "agent.security.credentials.user_has_provider_credential",
        AsyncMock(return_value=False),
    ):
        out = await router_node(_state())

    assert out["model"] == "claude-opus-4-7"
    assert out["routing_used"] is False
    assert out["routing_reason"] == "no_cheap_credentials"


@pytest.mark.asyncio
async def test_same_provider_skips_credential_check():
    """If cheap_model is same-provider as primary, no extra DB call."""
    cred_mock = AsyncMock()
    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(return_value={"enabled": True, "cheap_model": "anthropic/claude-haiku-4-5"}),
    ), patch(
        "agent.security.credentials.user_has_provider_credential", cred_mock
    ):
        out = await router_node(_state(model="anthropic/claude-opus-4-7"))

    assert out["model"] == "anthropic/claude-haiku-4-5"
    assert out["routing_used"] is True
    cred_mock.assert_not_called()


@pytest.mark.asyncio
async def test_complex_message_stays_primary():
    """Heuristic rejection is surfaced as routing_reason=complex_heuristic."""
    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(return_value={"enabled": True, "cheap_model": "openai/gpt-4o-mini"}),
    ):
        out = await router_node(
            _state(messages=[{"role": "user", "content": "please debug this stacktrace"}])
        )

    assert out["model"] == "claude-opus-4-7"
    assert out["routing_used"] is False
    assert out["routing_reason"] == "complex_heuristic"


@pytest.mark.asyncio
async def test_ab_row_id_triggers_mark_routing():
    """When running under an experiment, fire-and-forget UPDATE is scheduled."""
    marks: list[dict] = []

    async def fake_mark(row_id, *, routing_used, routing_reason, routing_picked_model):
        marks.append(
            {
                "row_id": row_id,
                "routing_used": routing_used,
                "routing_reason": routing_reason,
                "routing_picked_model": routing_picked_model,
            }
        )

    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(return_value={"enabled": True, "cheap_model": "openai/gpt-4o-mini"}),
    ), patch(
        "agent.security.credentials.user_has_provider_credential",
        AsyncMock(return_value=True),
    ), patch("agent.runners.dispatcher._mark_routing", fake_mark):
        await router_node(_state(ab_row_id="row-xyz"))

    # Give create_task a tick to run.
    import asyncio
    await asyncio.sleep(0)

    assert len(marks) == 1
    assert marks[0]["row_id"] == "row-xyz"
    assert marks[0]["routing_used"] is True


@pytest.mark.asyncio
async def test_no_ab_row_id_skips_mark_routing():
    marks: list[dict] = []

    async def fake_mark(row_id, *, routing_used, routing_reason, routing_picked_model):
        marks.append({"row_id": row_id})

    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(return_value={"enabled": True, "cheap_model": "openai/gpt-4o-mini"}),
    ), patch(
        "agent.security.credentials.user_has_provider_credential",
        AsyncMock(return_value=True),
    ), patch("agent.runners.dispatcher._mark_routing", fake_mark):
        await router_node(_state())  # ab_row_id default ""

    import asyncio
    await asyncio.sleep(0)

    assert marks == []


@pytest.mark.asyncio
async def test_routing_error_falls_through_to_primary():
    """Any exception in routing must not break the turn."""
    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(side_effect=RuntimeError("boom")),
    ):
        out = await router_node(_state())

    assert out["model"] == "claude-opus-4-7"
    assert out["routing_reason"] == "not_evaluated"
    assert out["routing_used"] is False


@pytest.mark.asyncio
async def test_de_complex_message_stays_primary():
    """End-to-end sanity check that ADR-001 G1 bilingual keywords still block DE."""
    with patch(
        "agent.security.credentials.get_user_smart_routing_config",
        AsyncMock(return_value={"enabled": True, "cheap_model": "openai/gpt-4o-mini"}),
    ):
        out = await router_node(
            _state(messages=[{"role": "user", "content": "analysiere mein portfolio"}])
        )

    assert out["routing_used"] is False
    assert out["routing_reason"] == "complex_heuristic"
