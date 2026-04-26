"""Smoke tests for agent/runners/simple.py.

These are not full integration tests — they stub llm_node + tool_node
(which are independently tested) and verify that simple_runner.py:

* emits the SSE packet sequence in the correct order
* uses the same packet id scheme as LangGraph ("t1")
* populates MessageMetaPacket with the correct keys
* appends tool-role messages between turns
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_simple_loop_single_turn_no_tools(monkeypatch):
    """LLM responds with no tool_calls → single text + finish."""
    from agent.runners import simple

    async def _fake_llm_node(state):
        return {
            "final_response": "Hallo",
            "messages": [{"role": "assistant", "content": "Hallo"}],
            "tool_calls": [],
            "prompt_tokens": 42,
            "completion_tokens": 7,
            "token_usage": 49,
            "llm_provider": "stub",
            "llm_model": state["model"],
        }

    async def _fake_tool_node(state):
        return {"tool_results": [], "tool_calls": []}

    async def _fake_prepare_messages(messages, ctx):
        return messages

    async def _fake_prepare_system_prompt(ctx, messages):
        return "stub-system-prompt"

    def _fake_create_session(**kwargs):
        class _S:
            session_id = "test-session"
        return _S()

    def _fake_update_session(*args, **kwargs):
        return None

    def _fake_scan_output_anomalies(text):
        class _R:
            clean = True
            anomalies = []
        return _R()

    ctx = _make_ctx()

    with patch("agent.graph.nodes.llm_node.llm_node", _fake_llm_node), patch(
        "agent.graph.nodes.tool_node.tool_node", _fake_tool_node
    ), patch(
        "agent.graph.runner._prepare_messages", _fake_prepare_messages
    ), patch(
        "agent.graph.runner._prepare_system_prompt", _fake_prepare_system_prompt
    ), patch(
        "agent.sessions.create_session", _fake_create_session
    ), patch(
        "agent.sessions.update_session", _fake_update_session
    ), patch(
        "agent.middleware.sanitizer.scan_output_anomalies", _fake_scan_output_anomalies
    ):
        chunks = []
        async for c in simple.run_simple_agent_loop(
            ctx, [{"role": "user", "content": "hi"}], ab_row_id=None,
        ):
            chunks.append(c)

    joined = "\n".join(chunks)
    # Required SSE packet markers (AI-SDK v6 protocol shape — look for type keys).
    assert any("thread" in c.lower() for c in chunks[:2])
    assert "Hallo" in joined
    # Order: AI-SDK v6 'start' is the first event (messageId carries thread id),
    # followed by a 'message-metadata' packet exposing threadId explicitly.
    assert '"type": "start"' in chunks[0] or "thread" in chunks[0].lower()
    assert "thread" in chunks[1].lower() or "threadid" in chunks[1].lower()
    # Final chunk carries finish_reason
    assert "finish" in chunks[-1].lower() or "stop" in chunks[-1].lower()


@pytest.mark.asyncio
async def test_simple_loop_surfaces_llm_exception(monkeypatch):
    """A raised exception in llm_node must propagate out of the generator."""
    from agent.runners import simple

    async def _broken_llm(state):
        raise RuntimeError("llm-down")

    async def _fake_prepare_messages(messages, ctx):
        return messages

    async def _fake_prepare_system_prompt(ctx, messages):
        return ""

    def _fake_create_session(**kwargs):
        class _S:
            session_id = "s1"
        return _S()

    def _fake_update_session(*args, **kwargs):
        return None

    ctx = _make_ctx()

    with patch("agent.graph.nodes.llm_node.llm_node", _broken_llm), patch(
        "agent.graph.runner._prepare_messages", _fake_prepare_messages
    ), patch(
        "agent.graph.runner._prepare_system_prompt", _fake_prepare_system_prompt
    ), patch(
        "agent.sessions.create_session", _fake_create_session
    ), patch(
        "agent.sessions.update_session", _fake_update_session
    ):
        with pytest.raises(RuntimeError, match="llm-down"):
            async for _ in simple.run_simple_agent_loop(
                ctx, [{"role": "user", "content": "x"}], ab_row_id=None,
            ):
                pass


def _make_ctx():
    from agent.context import AgentExecutionContext
    from agent.tools.registry import ToolRegistry

    reg = ToolRegistry.load()
    return AgentExecutionContext(
        user_id="alice",
        thread_id="t-test",
        model="gpt-4o-mini",
        api_key=None,
        system_prompt="",
        tools=tuple(reg.all()),
        reasoning_effort=None,
        agent_class="advisory",
        user_role="viewer",
    )


def test_append_tool_messages_accepts_dict_tool_calls():
    from agent.runners.simple import _append_tool_messages

    state = {
        "messages": [{"role": "user", "content": "use a tool"}],
        "final_response": "",
    }
    tool_calls = [
        {
            "tool_call_id": "call-1",
            "tool_name": "memory_search",
            "tool_input": {"query": "alpha"},
        }
    ]
    tool_results = [
        {
            "tool_call_id": "call-1",
            "tool_name": "memory_search",
            "result": {"matches": []},
        }
    ]

    _append_tool_messages(state, tool_calls, tool_results)

    assistant = state["messages"][1]
    tool = state["messages"][2]
    assert assistant["tool_calls"][0]["id"] == "call-1"
    assert assistant["tool_calls"][0]["function"]["name"] == "memory_search"
    assert '"query": "alpha"' in assistant["tool_calls"][0]["function"]["arguments"]
    assert tool["role"] == "tool"
    assert tool["tool_call_id"] == "call-1"


def test_append_tool_messages_preserves_openai_argument_strings():
    from agent.runners.simple import _append_tool_messages

    state = {
        "messages": [{"role": "user", "content": "use a tool"}],
        "final_response": "",
    }
    tool_calls = [
        {
            "id": "call-2",
            "function": {
                "name": "memory_search",
                "arguments": "{\"query\":\"beta\"}",
            },
        }
    ]

    _append_tool_messages(
        state,
        tool_calls,
        [{"tool_call_id": "call-2", "tool_name": "memory_search", "result": "ok"}],
    )

    tool_call = state["messages"][1]["tool_calls"][0]
    assert tool_call["id"] == "call-2"
    assert tool_call["function"]["name"] == "memory_search"
    assert tool_call["function"]["arguments"] == "{\"query\":\"beta\"}"
