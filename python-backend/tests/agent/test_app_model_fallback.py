from __future__ import annotations

import pytest

from agent import app


@pytest.mark.asyncio
async def test_stream_agent_loop_uses_env_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    async def fake_get_user_default_model(_user_id: str) -> None:
        return None

    async def fake_get_user_api_key(_user_id: str, _provider: str) -> None:
        return None

    async def fake_run_agent_loop(ctx, _messages):
        captured["model"] = ctx.model
        yield 'data: {"type":"text-delta","delta":"ok"}\n\n'

    class FakeRegistry:
        @staticmethod
        def load() -> FakeRegistry:
            return FakeRegistry()

        def all(self) -> tuple[()]:
            return ()

    monkeypatch.setenv("AGENT_DEFAULT_UTILITY_MODEL", "openrouter/openrouter/free")
    monkeypatch.setattr(
        "agent.security.credentials.get_user_default_model",
        fake_get_user_default_model,
    )
    monkeypatch.setattr("agent.security.credentials.get_user_api_key", fake_get_user_api_key)
    monkeypatch.setattr("agent.tools.registry.ToolRegistry", FakeRegistry)
    monkeypatch.setattr(
        "agent.runners.dispatcher.run_agent_loop_with_variant",
        fake_run_agent_loop,
    )

    req = app.AgentChatRequest(message="hi", threadId="thread-1")
    chunks = [
        chunk
        async for chunk in app._stream_agent_loop(
            req,
            system_prompt="system",
            thread_id="thread-1",
            user_id="default",
        )
    ]

    assert captured["model"] == "openrouter/openrouter/free"
    assert chunks == ['data: {"type":"text-delta","delta":"ok"}\n\n']


@pytest.mark.asyncio
async def test_stream_agent_loop_applies_a2a_child_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_get_user_default_model(_user_id: str) -> None:
        return None

    async def fake_get_user_api_key(_user_id: str, _provider: str) -> None:
        return None

    async def fake_run_agent_loop(ctx, _messages):
        captured["memory_write_policy"] = ctx.memory_write_policy
        captured["child_memory_write_allowed"] = ctx.child_memory_write_allowed
        captured["parent_thread_id"] = ctx.parent_thread_id
        captured["spawn_depth"] = ctx.spawn_depth
        captured["tools"] = [tool.name for tool in ctx.tools]
        yield 'data: {"type":"text-delta","delta":"ok"}\n\n'

    class _Tool:
        def __init__(self, name: str) -> None:
            self.name = name

    class FakeRegistry:
        @staticmethod
        def load() -> FakeRegistry:
            return FakeRegistry()

        def all(self) -> tuple[_Tool, ...]:
            return (
                _Tool("semantic_lookup"),
                _Tool("memory_add"),
                _Tool("send_message"),
            )

    monkeypatch.setenv("AGENT_DEFAULT_UTILITY_MODEL", "openrouter/openrouter/free")
    monkeypatch.setattr(
        "agent.security.credentials.get_user_default_model",
        fake_get_user_default_model,
    )
    monkeypatch.setattr("agent.security.credentials.get_user_api_key", fake_get_user_api_key)
    monkeypatch.setattr("agent.tools.registry.ToolRegistry", FakeRegistry)
    monkeypatch.setattr(
        "agent.runners.dispatcher.run_agent_loop_with_variant",
        fake_run_agent_loop,
    )

    req = app.AgentChatRequest(
        message="child task",
        threadId="a2a-child-1",
        context=(
            "Delegated from Matrix orchestrator; role:researcher; "
            "parent_thread_id:parent-1; spawn_depth:1; max_spawn_depth:1; "
            "memory_scope:explicit_context_only; context_mode:isolated; "
            "allowed_tools:semantic_lookup; memory_write_policy:parent_only; "
            "approval_mode:non_interactive_auto_deny"
        ),
    )
    chunks = [
        chunk
        async for chunk in app._stream_agent_loop(
            req,
            system_prompt="system",
            thread_id="a2a-child-1",
            user_id="default",
        )
    ]

    assert captured["memory_write_policy"] == "parent_only"
    assert captured["child_memory_write_allowed"] is False
    assert captured["parent_thread_id"] == "parent-1"
    assert captured["spawn_depth"] == 1
    assert captured["tools"] == ["semantic_lookup"]
    assert chunks == ['data: {"type":"text-delta","delta":"ok"}\n\n']
