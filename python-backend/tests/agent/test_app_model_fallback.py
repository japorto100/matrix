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
