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
            isinstance(item, dict)
            and item.get("cache_control", {}).get("type") == "ephemeral"
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
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "a"},
                {"type": "text", "text": "b"},
            ],
        },
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
                _hidden_params={
                    "additional_headers": {
                        "x-request-id": "req-llm-1",
                        "x-ratelimit-limit-requests": "100",
                        "x-ratelimit-remaining-requests": "99",
                        "x-ratelimit-reset-requests": "30",
                    }
                },
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
    monkeypatch.setattr(
        "agent.tracing.turn_span", lambda *_args, **_kwargs: _FakeSpan()
    )
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
    assert result["request_telemetry"][0]["contract"] == "provider-request-telemetry/v1"
    response_metadata = result["request_telemetry"][0]["metadata"]["response"]
    assert response_metadata["request_id"] == "req-llm-1"
    assert response_metadata["rate_limits"][0]["window"] == "requests"
    assert response_metadata["rate_limits"][0]["remaining"] == 99
    assert result["runtime_events"][0]["contract"] == "agent-runtime-event/v1"
    assert "say ok" not in str(result["request_telemetry"][0])


@pytest.mark.asyncio
async def test_llm_node_emits_prompt_cache_break_runtime_event(monkeypatch):
    from agent.graph.nodes import llm_node as llm_module

    class _FakeCompletions:
        async def create(self, **kwargs):
            message = SimpleNamespace(content="ok", tool_calls=None)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
                usage=SimpleNamespace(
                    prompt_tokens=10,
                    completion_tokens=2,
                    total_tokens=12,
                    prompt_tokens_details={"cached_tokens": 10},
                ),
                model=kwargs["model"],
                _hidden_params={"additional_headers": {"x-request-id": "req-cache-1"}},
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

    monkeypatch.setattr(llm_module, "get_litellm_client", lambda: _FakeClient())
    monkeypatch.setattr(llm_module, "get_credential_pool", lambda: _FakePool())
    monkeypatch.setattr(
        "agent.tracing.turn_span", lambda *_args, **_kwargs: _FakeSpan()
    )
    monkeypatch.setattr("agent.audit.logger.audit_log", _noop_audit_log)

    result = await llm_module.llm_node(
        {
            "model": "openrouter/test-model",
            "messages": [{"role": "user", "content": "say ok"}],
            "system_prompt": "test",
            "thread_id": "t-cache",
            "iteration": 1,
            "tool_definitions": [],
            "user_id": "anonymous",
            "request_telemetry": [
                {
                    "model": "openrouter/test-model",
                    "prompt_digest": "prev-prompt",
                    "prompt_layout_digest": "prev-layout",
                    "tool_catalog_digest": "prev-tools",
                    "usage": {"cache_read_tokens": 100},
                }
            ],
        }
    )

    cache_event = next(
        event
        for event in result["runtime_events"]
        if event["name"] == "llm.prompt_cache_break"
    )
    assert cache_event["kind"] == "llm"
    assert cache_event["status"] == "active"
    assert cache_event["metadata"]["request_id"] == "req-cache-1"
    assert "prompt_layout_changed" in cache_event["metadata"]["cache_break_reasons"]
    assert "cache_read_drop" in cache_event["metadata"]["cache_break_reasons"]


@pytest.mark.asyncio
async def test_llm_node_emits_route_decision_for_tool_use(monkeypatch):
    from agent.audit.logger import AuditAction
    from agent.graph.nodes import llm_node as llm_module

    audit_events: list[dict] = []

    class _FakeCompletions:
        async def create(self, **kwargs):
            message = SimpleNamespace(
                content="",
                tool_calls=[
                    SimpleNamespace(
                        id="call-1",
                        function=SimpleNamespace(
                            name="memory_search",
                            arguments='{"query":"risk preference"}',
                        ),
                    )
                ],
            )
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

    async def _capture_audit_log(**kwargs):
        audit_events.append(kwargs)

    monkeypatch.setenv("AGENT_MAX_OUTPUT_TOKENS", "64")
    monkeypatch.setattr(llm_module, "get_litellm_client", lambda: _FakeClient())
    monkeypatch.setattr(llm_module, "get_credential_pool", lambda: _FakePool())
    monkeypatch.setattr(
        "agent.tracing.turn_span", lambda *_args, **_kwargs: _FakeSpan()
    )
    monkeypatch.setattr("agent.audit.logger.audit_log", _capture_audit_log)

    result = await llm_module.llm_node(
        {
            "model": "openrouter/test-model",
            "messages": [{"role": "user", "content": "check memory"}],
            "system_prompt": "test",
            "thread_id": "t-route",
            "iteration": 0,
            "tool_definitions": [
                {
                    "name": "memory_search",
                    "description": "Search memory",
                    "input_schema": {"type": "object"},
                }
            ],
            "user_id": "anonymous",
            "runner_variant": "simple",
            "routing_reason": "simple_turn",
            "routing_used": True,
            "routing_picked_model": "openrouter/test-model",
        }
    )

    route_event = next(
        event for event in audit_events if event["action"] == AuditAction.ROUTE_DECISION
    )
    response_event = next(
        event for event in audit_events if event["action"] == AuditAction.LLM_RESPONSE
    )
    assert route_event["thread_id"] == "t-route"
    assert route_event["metadata"]["runner"] == "simple"
    assert route_event["metadata"]["decision"] == "tool_use"
    assert route_event["metadata"]["route_taxonomy"] == "retrieval_answer"
    assert route_event["metadata"]["delegation_decision"] == "none"
    assert route_event["metadata"]["delegate_kind"] is None
    assert route_event["metadata"]["spawn_depth"] == 0
    assert route_event["metadata"]["max_spawn_depth"] == 0
    assert route_event["metadata"]["fallback_reason"] == "subagents_disabled"
    assert route_event["metadata"]["allowed_tools"] == ["memory_search"]
    assert route_event["metadata"]["memory_scope"] == "current_user"
    assert route_event["metadata"]["tool_names"] == ["memory_search"]
    assert route_event["metadata"]["memory_route_requested"] is True
    assert route_event["metadata"]["retrieval_route_requested"] is True
    assert response_event["metadata"]["runtime_events"][0]["kind"] == "llm"
    assert response_event["metadata"]["runtime_events"][0]["status"] == "completed"
    assert result["tool_calls"][0]["tool_name"] == "memory_search"


@pytest.mark.asyncio
async def test_llm_node_omits_known_unsupported_provider_fields(monkeypatch):
    from agent.graph.nodes import llm_node as llm_module

    captured: dict = {}
    span_events: list[tuple[str, dict]] = []

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

        def add_event(self, name, attrs=None):
            span_events.append((name, attrs or {}))

        def track_generation(self, *_args, **_kwargs):
            return None

    async def _noop_audit_log(**_kwargs):
        return None

    monkeypatch.setattr(llm_module, "get_litellm_client", lambda: _FakeClient())
    monkeypatch.setattr(llm_module, "get_credential_pool", lambda: _FakePool())
    monkeypatch.setattr(
        llm_module,
        "model_capabilities",
        lambda _model: {
            "known_to_litellm": True,
            "supports_tools": False,
            "supports_reasoning_effort": False,
        },
    )
    monkeypatch.setattr(
        "agent.tracing.turn_span", lambda *_args, **_kwargs: _FakeSpan()
    )
    monkeypatch.setattr("agent.audit.logger.audit_log", _noop_audit_log)

    result = await llm_module.llm_node(
        {
            "model": "openrouter/no-tools-model",
            "messages": [{"role": "user", "content": "say ok"}],
            "system_prompt": "test",
            "thread_id": "",
            "iteration": 0,
            "tool_definitions": [
                {
                    "name": "memory_search",
                    "description": "Search memory",
                    "input_schema": {"type": "object"},
                }
            ],
            "reasoning_effort": "high",
            "user_id": "anonymous",
        }
    )

    assert "tools" not in captured
    assert "reasoning_effort" not in captured
    assert result["final_response"] == "ok"
    omitted = [
        attrs["field"]
        for name, attrs in span_events
        if name == "provider_field_omitted"
    ]
    assert omitted == ["tools", "reasoning_effort"]


@pytest.mark.asyncio
async def test_llm_node_keeps_fields_when_capabilities_unknown(monkeypatch):
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

    monkeypatch.setattr(llm_module, "get_litellm_client", lambda: _FakeClient())
    monkeypatch.setattr(llm_module, "get_credential_pool", lambda: _FakePool())
    monkeypatch.setattr(
        llm_module,
        "model_capabilities",
        lambda _model: {
            "known_to_litellm": False,
            "supports_tools": False,
            "supports_reasoning_effort": False,
        },
    )
    monkeypatch.setattr(
        "agent.tracing.turn_span", lambda *_args, **_kwargs: _FakeSpan()
    )
    monkeypatch.setattr("agent.audit.logger.audit_log", _noop_audit_log)

    await llm_module.llm_node(
        {
            "model": "custom/provider-model",
            "messages": [{"role": "user", "content": "say ok"}],
            "system_prompt": "test",
            "thread_id": "",
            "iteration": 0,
            "tool_definitions": [
                {
                    "name": "memory_search",
                    "description": "Search memory",
                    "input_schema": {"type": "object"},
                }
            ],
            "reasoning_effort": "high",
            "user_id": "anonymous",
        }
    )

    assert "tools" in captured
    assert captured["reasoning_effort"] == "high"
