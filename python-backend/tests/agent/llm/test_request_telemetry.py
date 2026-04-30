from __future__ import annotations

from types import SimpleNamespace

from agent.llm.request_telemetry import (
    build_request_telemetry,
    detect_cache_break,
    digest_prompt,
    digest_tool_catalog,
    normalize_usage,
    response_metadata,
)


def test_prompt_digest_separates_content_from_layout() -> None:
    a = [{"role": "user", "content": "hello"}]
    b = [{"role": "user", "content": "world"}]

    assert digest_prompt(a, include_text=True) != digest_prompt(b, include_text=True)
    assert digest_prompt(a, include_text=False) == digest_prompt(b, include_text=False)


def test_tool_digest_uses_schema_shape() -> None:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "memory_search",
                "description": "Search memory",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }
    ]

    assert len(digest_tool_catalog(tools)) == 64


def test_normalize_usage_preserves_unknown_fields() -> None:
    usage = SimpleNamespace(
        prompt_tokens=10,
        completion_tokens=3,
        prompt_tokens_details={"cached_tokens": 4},
        cache_creation_input_tokens=1,
    )

    normalized = normalize_usage(usage)

    assert normalized.prompt_tokens == 10
    assert normalized.input_tokens == 5
    assert normalized.completion_tokens == 3
    assert normalized.output_tokens == 3
    assert normalized.total_tokens == 13
    assert normalized.cache_read_tokens == 4
    assert normalized.cache_write_tokens == 1
    assert "reasoning_tokens" in normalized.unknown_fields
    assert "cache_write_tokens" not in normalized.unknown_fields


def test_normalize_usage_keeps_fresh_input_unknown_when_cache_unknown() -> None:
    normalized = normalize_usage({"prompt_tokens": 10, "completion_tokens": 3})

    assert normalized.prompt_tokens == 10
    assert normalized.input_tokens is None
    assert normalized.output_tokens == 3
    assert "input_tokens" in normalized.unknown_fields
    assert "cache_read_tokens" in normalized.unknown_fields
    assert "cache_write_tokens" in normalized.unknown_fields


def test_normalize_usage_marks_output_unknown_when_completion_missing() -> None:
    normalized = normalize_usage({"prompt_tokens": 10})

    assert normalized.completion_tokens is None
    assert normalized.output_tokens is None
    assert "completion_tokens" in normalized.unknown_fields
    assert "output_tokens" in normalized.unknown_fields


def test_detect_cache_break_reasons() -> None:
    previous = {
        "model": "m1",
        "prompt_digest": "p1",
        "prompt_layout_digest": "l1",
        "tool_catalog_digest": "t1",
    }

    assert detect_cache_break(
        previous=previous,
        prompt_digest="p2",
        prompt_layout_digest="l1",
        tool_catalog_digest="t2",
        model="m2",
    ) == ["model_changed", "prompt_content_changed", "tool_catalog_changed"]


def test_build_request_telemetry_has_no_raw_prompt() -> None:
    telemetry = build_request_telemetry(
        provider="openrouter",
        model="openrouter/test",
        router="simple",
        thread_id="t1",
        iteration=0,
        messages=[{"role": "user", "content": "private prompt"}],
        tools=[],
        usage={"prompt_tokens": 2, "completion_tokens": 1},
    )

    assert telemetry["contract"] == "provider-request-telemetry/v1"
    assert telemetry["usage"]["total_tokens"] == 3
    assert "private prompt" not in str(telemetry)


def test_build_request_telemetry_redacts_free_form_metadata() -> None:
    telemetry = build_request_telemetry(
        provider="openrouter",
        model="openrouter/test",
        router="simple",
        thread_id="t1",
        iteration=0,
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        usage={"prompt_tokens": 2, "completion_tokens": 1},
        metadata={
            "response": {"request_id": "req-1"},
            "api_key": "sk-abc1234567890defghijklmn",
            "headers": {"authorization": "Bearer secret"},
            "provider_specific": {"reasoning_effort": "high"},
            "notes": "token sk-abc1234567890defghijklmn",
        },
    )

    assert telemetry["metadata"] == {
        "response": {"request_id": "req-1"},
        "notes": "token sk-abc...klmn",
    }
    assert "reasoning_effort" not in str(telemetry)
    assert "authorization" not in str(telemetry).lower()


def test_response_metadata_extracts_redacted_request_and_rate_limits() -> None:
    response = SimpleNamespace(
        _hidden_params={
            "additional_headers": {
                "x-request-id": "req-123",
                "openrouter-processing-ms": "42.5",
            }
        }
    )
    bucket = SimpleNamespace(
        window="requests",
        limit=100,
        remaining=25,
        reset_seconds=30.0,
        usage_pct=75.0,
        provider="openrouter",
        provider_key_id="opaque-key-id",
    )

    metadata = response_metadata(
        response,
        rate_limit_buckets=[bucket],
        duration_ms=51.23456,
    )

    assert metadata["request_id"] == "req-123"
    assert metadata["provider_processing_ms"] == 42.5
    assert metadata["duration_ms"] == 51.235
    assert metadata["rate_limits"][0]["window"] == "requests"
    assert metadata["rate_limits"][0]["remaining"] == 25
    assert "additional_headers" not in str(metadata)
