from __future__ import annotations

from agent.control.prompt_cache import (
    build_prompt_cache_aggregate_model,
    build_prompt_cache_read_model,
)


def _audit_event(**overrides):
    event = {
        "id": 1,
        "timestamp": "2026-04-30T10:00:00+00:00",
        "thread_id": "thread-1",
        "metadata": {
            "request_telemetry": {
                "contract": "provider-request-telemetry/v1",
                "provider": "openrouter",
                "model": "provider/model",
                "router": "langgraph",
                "transport": "litellm_chat_completions",
                "cache_retention": "ephemeral_breakpoints",
                "stream_strategy": "non_streaming",
                "thread_id": "thread-1",
                "iteration": 2,
                "prompt_digest": "prompt-a",
                "prompt_layout_digest": "layout-a",
                "system_prompt_digest": "system-a",
                "tool_catalog_digest": "tools-a",
                "tool_count": 2,
                "tool_names": ["memory_search", "semantic_lookup"],
                "cache_break_reasons": ["tool_catalog_changed"],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                    "cache_read_tokens": 40,
                    "cache_write_tokens": 5,
                    "unknown_fields": ["reasoning_tokens"],
                },
            }
        },
    }
    event.update(overrides)
    return event


def test_prompt_cache_read_model_summarizes_usage_and_breaks() -> None:
    model = build_prompt_cache_read_model(audit_events=[_audit_event()])

    assert model["contract"] == "prompt-cache-read-model/v1"
    assert model["summary"]["requests"] == 1
    assert model["summary"]["cache_impacts"] == 0
    assert model["summary"]["cache_read_tokens"] == 40
    assert model["summary"]["cache_write_tokens"] == 5
    assert model["summary"]["total_tokens"] == 120
    assert model["cache_break_reasons"] == {"tool_catalog_changed": 1}
    assert model["by_provider"] == {"openrouter": 1}
    assert model["by_thread"]["thread-1"]["requests"] == 1
    assert model["by_thread"]["thread-1"]["cache_read_tokens"] == 40
    assert model["by_thread"]["thread-1"]["cache_breaks"] == 1
    assert model["by_thread"]["thread-1"]["providers"] == ["openrouter"]
    item = model["items"][0]
    assert item["links"]["ops_event"] == "/control/ops?session=thread-1"
    assert item["links"]["context"] == "/control/context?thread_id=thread-1"
    assert item["transport"] == "litellm_chat_completions"
    assert item["cache_retention"] == "ephemeral_breakpoints"
    assert item["stream_strategy"] == "non_streaming"
    assert item["system_prompt_digest"] == "system-a"
    assert item["tool_count"] == 2
    assert item["tool_names"] == ["memory_search", "semantic_lookup"]
    assert model["by_thread"]["thread-1"]["first_timestamp"] == (
        "2026-04-30T10:00:00+00:00"
    )


def test_prompt_cache_read_model_preserves_unknown_cache_fields() -> None:
    event = _audit_event(
        metadata={
            "request_telemetry": {
                "provider": "provider",
                "model": "model",
                "usage": {"unknown_fields": ["cache_read_tokens", "cache_write_tokens"]},
            }
        }
    )

    model = build_prompt_cache_read_model(audit_events=[event])

    assert model["summary"]["unknown_cache_fields"] == 2
    assert model["items"][0]["usage"]["unknown_fields"] == [
        "cache_read_tokens",
        "cache_write_tokens",
    ]


def test_prompt_cache_read_model_surfaces_cache_impacts() -> None:
    event = _audit_event(
        metadata={
            "cache_impact": {
                "contract": "agent-cache-impact/v1",
                "source": "mcp_reload",
                "reason": "mcp_descriptor_catalog_reloaded",
                "previous_digest": "old",
                "next_digest": "new",
                "previous_digest_known": True,
                "changed": True,
                "action": "rebind_required",
                "scope": {"server_id": "matrix-internal"},
                "details": {"tool_count": 1},
            },
            "runtime_events": [
                {
                    "metadata": {
                        "cache_impact": {
                            "contract": "agent-cache-impact/v1",
                            "source": "mcp_reload",
                            "reason": "mcp_descriptor_catalog_reloaded",
                            "previous_digest": "old",
                            "next_digest": "new",
                            "previous_digest_known": True,
                            "changed": True,
                            "action": "rebind_required",
                        }
                    }
                }
            ],
        }
    )

    model = build_prompt_cache_read_model(audit_events=[event])

    assert model["summary"]["cache_impacts"] == 1
    assert model["summary"]["cache_invalidations"] == 1
    assert model["by_thread"]["thread-1"]["cache_impacts"] == 1
    assert model["by_thread"]["thread-1"]["cache_invalidations"] == 1
    assert model["cache_impacts"][0]["source"] == "mcp_reload"
    assert model["cache_impacts"][0]["links"]["ops_event"] == "/control/ops?session=thread-1"


def test_prompt_cache_aggregate_model_rolls_up_all_threads() -> None:
    second = _audit_event(
        id=2,
        timestamp="2026-04-30T10:05:00+00:00",
        thread_id="thread-2",
        metadata={
            "request_telemetry": {
                "provider": "openrouter",
                "model": "provider/other",
                "thread_id": "thread-2",
                "cache_break_reasons": [],
                "usage": {
                    "prompt_tokens": 30,
                    "completion_tokens": 4,
                    "total_tokens": 34,
                    "cache_read_tokens": 20,
                    "cache_write_tokens": 0,
                    "unknown_fields": ["cache_write_tokens"],
                },
            }
        },
    )
    read_model = build_prompt_cache_read_model(audit_events=[_audit_event(), second])

    aggregate = build_prompt_cache_aggregate_model(read_model, user_id="alice")

    assert aggregate["contract"] == "prompt-cache-aggregate/v1"
    assert aggregate["user_id"] == "alice"
    assert aggregate["summary"]["threads"] == 2
    assert aggregate["summary"]["requests"] == 2
    assert aggregate["summary"]["cache_read_tokens"] == 60
    assert aggregate["summary"]["cache_write_tokens"] == 5
    assert aggregate["summary"]["providers"] == ["openrouter"]
    assert aggregate["summary"]["models"] == ["provider/model", "provider/other"]
    assert aggregate["by_thread"]["thread-2"]["last_timestamp"] == (
        "2026-04-30T10:05:00+00:00"
    )
