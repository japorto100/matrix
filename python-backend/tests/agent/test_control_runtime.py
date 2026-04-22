from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agent.context import AgentExecutionContext
from agent.control.context_runtime import build_context_blocks
from agent.graph import runner


def test_build_context_blocks_enriches_semantics() -> None:
    blocks, counts = build_context_blocks(
        [
            {
                "id": "raw-1",
                "text": "User said to remember the London preference.",
                "fact_type": "experience",
                "metadata": {
                    "source_ref": "session-001.jsonl#0",
                    "artifact_type": "chat_turn",
                    "source_type": "user_input",
                },
            },
            {
                "id": "derived-1",
                "text": "The user prefers London.",
                "fact_type": "opinion",
                "metadata": {"artifact_type": "preference"},
            },
        ]
    )

    assert len(blocks) == 2
    assert counts["personal_raw"] == 1
    assert counts["personal_derived"] == 1
    assert {block["sourceLayer"] for block in blocks} == {"personal_raw", "personal_derived"}
    derived = next(block for block in blocks if block["sourceLayer"] == "personal_derived")
    assert derived["groundingStatus"] == "ungrounded_derived"
    assert derived["status"] == "candidate"


@pytest.mark.asyncio
async def test_run_agent_loop_streams_real_message_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_prepare_system_prompt(
        ctx: AgentExecutionContext, messages: list[dict]
    ) -> str:
        return ctx.system_prompt

    async def fake_prepare_messages(
        messages: list[dict], ctx: AgentExecutionContext
    ) -> list[dict]:
        return messages

    class FakeGraph:
        async def ainvoke(self, initial_state: dict, config: dict) -> dict:
            return {
                **initial_state,
                "final_response": "Done.",
                "iteration": 2,
                "prompt_tokens": 321,
                "completion_tokens": 123,
                "reasoning_tokens": 17,
                "cached_tokens": 88,
                "token_usage": 444,
                "llm_provider": "openrouter",
                "llm_model": "openrouter/anthropic/claude-sonnet",
                "source_layer_counts": {"personal_raw": 2, "bridge_world": 1},
                "degradation_flags": ["NO_PERSONAL_KB"],
                "context_blocks": [
                    {
                        "id": "raw-1",
                        "title": "Chat Turn",
                        "preview": "hello",
                        "sourceLayer": "personal_raw",
                    }
                ],
                "tool_results": [],
            }

    import agent.sessions as sessions

    monkeypatch.setattr(runner, "_prepare_system_prompt", fake_prepare_system_prompt)
    monkeypatch.setattr(runner, "_prepare_messages", fake_prepare_messages)
    monkeypatch.setattr(runner, "create_agent_graph", lambda: FakeGraph())
    monkeypatch.setattr(
        sessions,
        "create_session",
        lambda **kwargs: SimpleNamespace(session_id="sess-1"),
    )
    monkeypatch.setattr(sessions, "update_session", lambda *args, **kwargs: None)

    ctx = AgentExecutionContext(
        user_id="u1",
        thread_id="thread-1",
        model="openrouter/anthropic/claude-sonnet",
        system_prompt="system",
        tools=(),
    )

    chunks = [chunk async for chunk in runner.run_agent_loop(ctx, [{"role": "user", "content": "Hi"}])]
    # AI-SDK v6: the runner emits an early thread-id message-metadata before
    # the real end-of-turn metadata. Pick the one that carries promptTokens.
    metadata_chunk = next(
        chunk
        for chunk in chunks
        if '"type": "message-metadata"' in chunk and "promptTokens" in chunk
    )
    payload = json.loads(metadata_chunk.removeprefix("data: ").strip())

    assert payload["messageMetadata"]["promptTokens"] == 321
    assert payload["messageMetadata"]["completionTokens"] == 123
    assert payload["messageMetadata"]["cachedTokens"] == 88
    assert payload["messageMetadata"]["provider"] == "openrouter"
    assert payload["messageMetadata"]["sourceLayerCounts"]["personal_raw"] == 2
    assert payload["messageMetadata"]["degradationFlags"] == ["NO_PERSONAL_KB"]
