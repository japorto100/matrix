"""Tests for exec-hermes §4.5 Anthropic prompt caching — system-prompt breakpoint.

The spec at specs/execution/exec-hermes.md §4.5 requires cache_control on
``System + letzte 3 non-system messages`` (four breakpoints). Earlier the
implementation only marked the last 3 messages regardless of role; on long
conversations the system prompt fell out of the rolling window and was never
cached. This file pins the fixed semantics.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.graph.nodes.llm_node import (
    _apply_anthropic_caching,
    _clean_assistant_content,
    _max_output_tokens_from_env,
    _model_may_use_ephemeral_cache,
    _resolve_model_name,
)


def _msg(role: str, text: str) -> dict:
    return {"role": role, "content": text}


def _has_cache_control(msg: dict) -> bool:
    content = msg.get("content")
    if isinstance(content, list):
        return any(
            isinstance(item, dict) and item.get("cache_control", {}).get("type") == "ephemeral"
            for item in content
        )
    return False


def test_system_prompt_always_cached_even_on_long_conversation():
    """System message at [0] keeps its breakpoint even when there are many
    non-system messages — the rolling window must not push it out."""
    messages = [_msg("system", "You are a helpful agent.")]
    for i in range(10):
        messages.append(_msg("user" if i % 2 == 0 else "assistant", f"turn {i}"))

    _apply_anthropic_caching(messages)

    assert _has_cache_control(messages[0]), (
        "system prompt must carry cache_control regardless of conversation length"
    )


def test_last_three_non_system_messages_cached():
    messages = [
        _msg("system", "sys"),
        _msg("user", "u1"),
        _msg("assistant", "a1"),
        _msg("user", "u2"),
        _msg("assistant", "a2"),
        _msg("user", "u3"),
    ]
    _apply_anthropic_caching(messages)

    # indices 3, 4, 5 = last three non-system messages → cached
    assert _has_cache_control(messages[3])
    assert _has_cache_control(messages[4])
    assert _has_cache_control(messages[5])
    # Older non-system messages must not be cached.
    assert not _has_cache_control(messages[1])
    assert not _has_cache_control(messages[2])


def test_short_conversation_caches_all_non_system():
    """When there are fewer than 3 non-system messages, all of them + system
    get cache_control (window is "last N where N ≤ 3")."""
    messages = [
        _msg("system", "sys"),
        _msg("user", "u1"),
    ]
    _apply_anthropic_caching(messages)
    assert _has_cache_control(messages[0])
    assert _has_cache_control(messages[1])


def test_empty_messages_safe_noop():
    messages: list[dict] = []
    _apply_anthropic_caching(messages)
    assert messages == []


def test_no_system_prompt_still_caches_last_three():
    messages = [
        _msg("user", "u1"),
        _msg("assistant", "a1"),
        _msg("user", "u2"),
        _msg("assistant", "a2"),
    ]
    _apply_anthropic_caching(messages)
    # last three
    assert _has_cache_control(messages[1])
    assert _has_cache_control(messages[2])
    assert _has_cache_control(messages[3])
    assert not _has_cache_control(messages[0])


def test_list_content_gets_cache_control_on_every_part():
    """For messages with already-list content (tool-result-style), each part
    gets cache_control so Anthropic can slice the breakpoint mid-message."""
    messages = [
        _msg("system", "sys"),
        {"role": "user", "content": [
            {"type": "text", "text": "a"},
            {"type": "text", "text": "b"},
        ]},
    ]
    _apply_anthropic_caching(messages)
    for item in messages[1]["content"]:
        assert item.get("cache_control", {}).get("type") == "ephemeral"


def test_non_anthropic_model_gate_returns_false():
    """Sanity: gate function controls whether caching runs at all."""
    assert _model_may_use_ephemeral_cache("claude-sonnet-4-6") is True
    assert _model_may_use_ephemeral_cache("openrouter/anthropic/claude-opus") is True
    assert _model_may_use_ephemeral_cache("openai/gpt-4o-mini") is False
    assert _model_may_use_ephemeral_cache("") is False


def test_clean_assistant_content_strips_provider_reasoning_markers():
    raw = "analysisNeed answer.assistantfinal**Result**\nEURUSD 4H"
    assert _clean_assistant_content(raw) == "**Result**\nEURUSD 4H"


def test_clean_assistant_content_leaves_normal_text_unchanged():
    text = "Final answer: EURUSD is on the 4H chart."
    assert _clean_assistant_content(text) == text


def test_clean_assistant_content_removes_textual_tool_call_block():
    raw = (
        "Stored.\n"
        "<tool_call>\n"
        '{"name": "memory_add", "arguments": {"content": "x"}}\n'
        "</tool_call>"
    )

    assert _clean_assistant_content(raw) == "Stored."


def test_clean_assistant_content_replaces_tool_call_only_output():
    raw = (
        "<tool_call>\n"
        '{"name": "memory_add", "arguments": {"content": "x"}}\n'
        "</tool_call>"
    )

    assert _clean_assistant_content(raw) == "Done."


def test_resolve_model_name_falls_back_to_env(monkeypatch):
    monkeypatch.delenv("AGENT_DEFAULT_MODEL", raising=False)
    monkeypatch.setenv("AGENT_DEFAULT_UTILITY_MODEL", "openrouter/test-model")
    assert _resolve_model_name("") == "openrouter/test-model"
    assert _resolve_model_name(" openrouter/explicit ") == "openrouter/explicit"


def test_max_output_tokens_env_default_and_disable(monkeypatch):
    monkeypatch.delenv("AGENT_MAX_OUTPUT_TOKENS", raising=False)
    assert _max_output_tokens_from_env() == 4096

    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "1024")
    assert _max_output_tokens_from_env() == 1024

    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "0")
    assert _max_output_tokens_from_env() is None

    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "invalid")
    assert _max_output_tokens_from_env() == 4096


@pytest.mark.asyncio
async def test_llm_node_passes_max_tokens_to_litellm(monkeypatch):
    from agent.graph.nodes import llm_node as llm_module

    captured: dict = {}

    class _FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            message = SimpleNamespace(content="ok", tool_calls=None)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
                usage=None,
                model=kwargs["model"],
            )

    class _FakeClient:
        chat = SimpleNamespace(completions=_FakeCompletions())

    class _FakePool:
        async def acquire(self, **_kwargs):
            return None

    class _FakeSpan:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def set_attribute(self, *_args, **_kwargs):
            return None

        def add_event(self, *_args, **_kwargs):
            return None

        def track_generation(self, *_args, **_kwargs):
            return None

    async def _noop_audit_log(**_kwargs):
        return None

    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "64")
    monkeypatch.setattr(llm_module, "get_litellm_client", lambda: _FakeClient())
    monkeypatch.setattr(llm_module, "get_credential_pool", lambda: _FakePool())
    monkeypatch.setattr("agent.tracing.turn_span", lambda *_args, **_kwargs: _FakeSpan())
    monkeypatch.setattr("agent.audit.logger.audit_log", _noop_audit_log)

    result = await llm_module.llm_node(
        {
            "model": "openrouter/test-model",
            "messages": [{"role": "user", "content": "say ok"}],
            "system_prompt": "test",
            "thread_id": "",
            "iteration": 0,
            "tool_definitions": [],
            "user_id": "anonymous",
        }
    )

    assert captured["max_tokens"] == 64
    assert captured["model"] == "openrouter/test-model"
    assert result["final_response"] == "ok"
