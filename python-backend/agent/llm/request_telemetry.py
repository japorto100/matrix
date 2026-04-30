"""Provider-agnostic request/cache telemetry helpers for LLM calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

REQUEST_TELEMETRY_CONTRACT = "provider-request-telemetry/v1"

_REQUEST_ID_HEADER_KEYS = (
    "x-request-id",
    "request-id",
    "x-openai-request-id",
    "x-litellm-request-id",
    "x-requestid",
)
_PROCESSING_MS_HEADER_KEYS = (
    "x-processing-ms",
    "openrouter-processing-ms",
    "x-litellm-response-duration-ms",
    "x-response-time-ms",
    "server-timing",
)
_FORBIDDEN_METADATA_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "auth_header",
    "bearer",
    "headers",
    "messages",
    "provider_specific",
    "raw_messages",
    "raw_prompt",
    "raw_reasoning",
    "raw_secret",
    "reasoning_block",
    "reasoning_content",
    "reasoning_trace",
    "request_telemetry",
    "resolved_secret",
    "secret",
    "secret_value",
    "thinking",
    "thinking_blocks",
}


@dataclass(frozen=True)
class UsageTelemetry:
    prompt_tokens: int | None = None
    input_tokens: int | None = None
    completion_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    unknown_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RequestTelemetry:
    provider: str
    model: str
    router: str
    transport: str
    cache_retention: str
    stream_strategy: str
    thread_id: str
    iteration: int
    prompt_digest: str
    prompt_layout_digest: str
    system_prompt_digest: str
    tool_catalog_digest: str
    tool_count: int
    tool_names: tuple[str, ...]
    usage: UsageTelemetry
    cache_break_reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    contract: str = REQUEST_TELEMETRY_CONTRACT

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["usage"] = self.usage.to_dict()
        return payload


def build_request_telemetry(
    *,
    provider: str,
    model: str,
    router: str,
    thread_id: str,
    iteration: int,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    usage: Any,
    previous: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    transport: str = "litellm",
    cache_retention: str = "provider_default",
    stream_strategy: str = "non_streaming",
) -> dict[str, Any]:
    """Build one redacted request telemetry envelope.

    Prompt text is never stored. `prompt_digest` hashes normalized content and
    `prompt_layout_digest` hashes role/content shape plus cache-control markers.
    """

    prompt_digest = digest_prompt(messages, include_text=True)
    layout_digest = digest_prompt(messages, include_text=False)
    system_digest = digest_system_prompt(messages)
    tool_digest = digest_tool_catalog(tools)
    tool_names = tuple(sorted(_tool_name(tool) for tool in tools if _tool_name(tool)))
    telemetry = RequestTelemetry(
        provider=provider,
        model=model,
        router=router,
        transport=str(transport or "unknown"),
        cache_retention=str(cache_retention or "unknown"),
        stream_strategy=str(stream_strategy or "unknown"),
        thread_id=thread_id,
        iteration=iteration,
        prompt_digest=prompt_digest,
        prompt_layout_digest=layout_digest,
        system_prompt_digest=system_digest,
        tool_catalog_digest=tool_digest,
        tool_count=len(tool_names),
        tool_names=tool_names,
        usage=normalize_usage(usage),
        cache_break_reasons=tuple(
            detect_cache_break(
                previous=previous,
                prompt_digest=prompt_digest,
                prompt_layout_digest=layout_digest,
                system_prompt_digest=system_digest,
                tool_catalog_digest=tool_digest,
                model=model,
                transport=str(transport or "unknown"),
                cache_retention=str(cache_retention or "unknown"),
                stream_strategy=str(stream_strategy or "unknown"),
            )
        ),
        metadata=_sanitize_metadata(metadata or {}),
    )
    return telemetry.to_dict()


def normalize_usage(usage: Any) -> UsageTelemetry:
    """Normalize LiteLLM/OpenAI-compatible usage objects without fabricating values."""

    raw = _to_mapping(usage)
    prompt_details = _to_mapping(raw.get("prompt_tokens_details"))
    completion_details = _to_mapping(raw.get("completion_tokens_details"))

    prompt = _int_or_none(raw.get("prompt_tokens") or raw.get("input_tokens"))
    completion = _int_or_none(
        raw.get("completion_tokens") or raw.get("output_tokens")
    )
    total = _int_or_none(raw.get("total_tokens"))
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion

    reasoning = _first_int(
        raw.get("reasoning_tokens"),
        completion_details.get("reasoning_tokens"),
        raw.get("completion_tokens_details_reasoning_tokens"),
    )
    cache_read = _first_int(
        raw.get("cache_read_tokens"),
        raw.get("cached_tokens"),
        prompt_details.get("cached_tokens"),
        prompt_details.get("cache_read_tokens"),
    )
    cache_write = _first_int(
        raw.get("cache_write_tokens"),
        raw.get("cache_creation_input_tokens"),
        prompt_details.get("cache_creation_input_tokens"),
        prompt_details.get("cache_write_tokens"),
    )
    input_tokens = None
    if prompt is not None and cache_read is not None and cache_write is not None:
        input_tokens = max(0, prompt - cache_read - cache_write)

    unknown: list[str] = []
    if prompt is None:
        unknown.append("prompt_tokens")
    if completion is None:
        unknown.append("completion_tokens")
        unknown.append("output_tokens")
    if total is None:
        unknown.append("total_tokens")
    if input_tokens is None:
        unknown.append("input_tokens")
    if reasoning is None:
        unknown.append("reasoning_tokens")
    if cache_read is None:
        unknown.append("cache_read_tokens")
    if cache_write is None:
        unknown.append("cache_write_tokens")

    return UsageTelemetry(
        prompt_tokens=prompt,
        input_tokens=input_tokens,
        completion_tokens=completion,
        output_tokens=completion,
        total_tokens=total,
        reasoning_tokens=reasoning,
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        unknown_fields=tuple(unknown),
    )


def digest_prompt(messages: list[dict[str, Any]], *, include_text: bool) -> str:
    normalized = [
        _normalize_message_for_digest(message, include_text=include_text)
        for message in messages
    ]
    return _sha256_json(normalized)


def digest_tool_catalog(tools: list[dict[str, Any]]) -> str:
    normalized = []
    for tool in tools:
        function = tool.get("function") if isinstance(tool, dict) else None
        source = function if isinstance(function, dict) else tool
        normalized.append(
            {
                "name": source.get("name"),
                "description_digest": _sha256_text(str(source.get("description") or "")),
                "schema_digest": _sha256_json(source.get("parameters") or source.get("input_schema") or {}),
            }
        )
    normalized.sort(key=lambda item: str(item.get("name") or ""))
    return _sha256_json(normalized)


def digest_system_prompt(messages: list[dict[str, Any]]) -> str:
    system_messages = [
        message for message in messages if str(message.get("role") or "") == "system"
    ]
    return digest_prompt(system_messages, include_text=True)


def detect_cache_break(
    *,
    previous: dict[str, Any] | None,
    prompt_digest: str,
    prompt_layout_digest: str,
    system_prompt_digest: str | None = None,
    tool_catalog_digest: str,
    model: str,
    transport: str | None = None,
    cache_retention: str | None = None,
    stream_strategy: str | None = None,
) -> list[str]:
    if not previous:
        return ["first_request"]
    reasons: list[str] = []
    if previous.get("model") != model:
        reasons.append("model_changed")
    if (
        transport is not None
        and "transport" in previous
        and previous.get("transport") != transport
    ):
        reasons.append("transport_changed")
    if (
        cache_retention is not None
        and "cache_retention" in previous
        and previous.get("cache_retention") != cache_retention
    ):
        reasons.append("cache_retention_changed")
    if (
        stream_strategy is not None
        and "stream_strategy" in previous
        and previous.get("stream_strategy") != stream_strategy
    ):
        reasons.append("stream_strategy_changed")
    if (
        system_prompt_digest is not None
        and "system_prompt_digest" in previous
        and previous.get("system_prompt_digest") != system_prompt_digest
    ):
        reasons.append("system_prompt_changed")
    if previous.get("prompt_layout_digest") != prompt_layout_digest:
        reasons.append("prompt_layout_changed")
    elif previous.get("prompt_digest") != prompt_digest:
        reasons.append("prompt_content_changed")
    if previous.get("tool_catalog_digest") != tool_catalog_digest:
        reasons.append("tool_catalog_changed")
    return reasons


def telemetry_span_attributes(telemetry: dict[str, Any]) -> dict[str, Any]:
    usage = telemetry.get("usage") if isinstance(telemetry.get("usage"), dict) else {}
    attrs: dict[str, Any] = {
        "request_telemetry.contract": str(
            telemetry.get("contract") or REQUEST_TELEMETRY_CONTRACT
        ),
        "request_telemetry.provider": str(telemetry.get("provider") or ""),
        "request_telemetry.model": str(telemetry.get("model") or ""),
        "request_telemetry.transport": str(telemetry.get("transport") or ""),
        "request_telemetry.cache_retention": str(
            telemetry.get("cache_retention") or ""
        ),
        "request_telemetry.stream_strategy": str(
            telemetry.get("stream_strategy") or ""
        ),
        "request_telemetry.prompt_digest": str(telemetry.get("prompt_digest") or ""),
        "request_telemetry.prompt_layout_digest": str(
            telemetry.get("prompt_layout_digest") or ""
        ),
        "request_telemetry.system_prompt_digest": str(
            telemetry.get("system_prompt_digest") or ""
        ),
        "request_telemetry.tool_catalog_digest": str(
            telemetry.get("tool_catalog_digest") or ""
        ),
        "request_telemetry.tool_count": int(telemetry.get("tool_count") or 0),
        "request_telemetry.tool_names": ",".join(
            str(name) for name in telemetry.get("tool_names") or ()
        ),
        "request_telemetry.cache_break_reasons": ",".join(
            str(reason) for reason in telemetry.get("cache_break_reasons") or ()
        ),
    }
    for key in (
        "prompt_tokens",
        "input_tokens",
        "completion_tokens",
        "output_tokens",
        "total_tokens",
        "reasoning_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
    ):
        value = usage.get(key)
        if value is not None:
            attrs[f"request_telemetry.{key}"] = int(value)
    unknown = usage.get("unknown_fields") or ()
    attrs["request_telemetry.unknown_fields"] = ",".join(str(item) for item in unknown)
    return attrs


def response_metadata(
    response: Any,
    *,
    rate_limit_buckets: list[Any] | tuple[Any, ...] = (),
    duration_ms: float | int | None = None,
) -> dict[str, Any]:
    """Return redacted provider response metadata for request telemetry."""

    headers = _response_headers(response)
    metadata: dict[str, Any] = {}
    request_id = _first_header(headers, _REQUEST_ID_HEADER_KEYS)
    if request_id:
        metadata["request_id"] = request_id
    processing_ms = _first_processing_ms(headers)
    if processing_ms is not None:
        metadata["provider_processing_ms"] = processing_ms
    if duration_ms is not None:
        metadata["duration_ms"] = round(float(duration_ms), 3)

    limits = [_rate_limit_bucket_metadata(bucket) for bucket in rate_limit_buckets]
    limits = [item for item in limits if item]
    if limits:
        metadata["rate_limits"] = limits
    return metadata


def _sanitize_metadata(value: Any) -> Any:
    """Redact free-form request metadata before it enters traces."""

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _metadata_key_forbidden(str(key)):
                continue
            sanitized[str(key)] = _sanitize_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_metadata(item) for item in value)
    if isinstance(value, str):
        from agent.security.redact import redact_sensitive_text

        return redact_sensitive_text(value)
    return value


def _metadata_key_forbidden(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return normalized in _FORBIDDEN_METADATA_KEYS


def _normalize_message_for_digest(
    message: dict[str, Any], *, include_text: bool
) -> dict[str, Any]:
    content = message.get("content")
    normalized: dict[str, Any] = {
        "role": message.get("role"),
        "content_shape": _content_shape(content, include_text=include_text),
    }
    if message.get("tool_calls"):
        normalized["tool_calls"] = _shape_only(message.get("tool_calls"))
    if message.get("tool_call_id"):
        normalized["tool_call_id"] = str(message.get("tool_call_id"))
    return normalized


def _content_shape(value: Any, *, include_text: bool) -> Any:
    if isinstance(value, str):
        return {
            "type": "text",
            "length": len(value),
            "text_digest": _sha256_text(value) if include_text else "",
        }
    if isinstance(value, list):
        return [_content_shape(item, include_text=include_text) for item in value]
    if isinstance(value, dict):
        shaped = {
            "type": value.get("type"),
            "keys": sorted(str(key) for key in value.keys()),
            "cache_control": value.get("cache_control", {}),
        }
        text = value.get("text")
        if isinstance(text, str):
            shaped["length"] = len(text)
            shaped["text_digest"] = _sha256_text(text) if include_text else ""
        return shaped
    return {"type": type(value).__name__}


def _response_headers(response: Any) -> dict[str, str]:
    hidden = getattr(response, "_hidden_params", None)
    if isinstance(hidden, dict) and isinstance(hidden.get("additional_headers"), dict):
        return {
            str(key).lower(): str(value)
            for key, value in hidden["additional_headers"].items()
        }
    raw_headers = getattr(response, "headers", None)
    if isinstance(raw_headers, dict):
        return {str(key).lower(): str(value) for key, value in raw_headers.items()}
    if isinstance(response, dict) and isinstance(response.get("headers"), dict):
        return {
            str(key).lower(): str(value)
            for key, value in response["headers"].items()
        }
    return {}


def _first_header(headers: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = headers.get(key)
        if value:
            return str(value)
    return ""


def _first_processing_ms(headers: dict[str, str]) -> float | None:
    for key in _PROCESSING_MS_HEADER_KEYS:
        value = headers.get(key)
        parsed = _parse_processing_ms(value)
        if parsed is not None:
            return parsed
    return None


def _parse_processing_ms(value: str | None) -> float | None:
    if not value:
        return None
    text = str(value).strip().lower()
    if text.endswith("ms"):
        text = text[:-2].strip()
    if text.endswith("s"):
        try:
            return round(float(text[:-1].strip()) * 1000, 3)
        except ValueError:
            return None
    if "dur=" in text:
        _, tail = text.split("dur=", 1)
        text = tail.split(",", 1)[0].split(";", 1)[0].strip()
    try:
        return round(float(text), 3)
    except ValueError:
        return None


def _rate_limit_bucket_metadata(bucket: Any) -> dict[str, Any]:
    window = str(getattr(bucket, "window", "") or "")
    if not window:
        return {}
    return {
        "window": window,
        "limit": int(getattr(bucket, "limit", 0) or 0),
        "remaining": int(getattr(bucket, "remaining", 0) or 0),
        "reset_seconds": float(getattr(bucket, "reset_seconds", 0.0) or 0.0),
        "usage_pct": round(float(getattr(bucket, "usage_pct", 0.0) or 0.0), 3),
        "provider": str(getattr(bucket, "provider", "") or ""),
        "provider_key_id": str(getattr(bucket, "provider_key_id", "") or ""),
    }


def _tool_name(tool: dict[str, Any]) -> str:
    function = tool.get("function") if isinstance(tool, dict) else None
    source = function if isinstance(function, dict) else tool
    if not isinstance(source, dict):
        return ""
    return str(source.get("name") or "")


def _shape_only(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _shape_only(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_shape_only(item) for item in value]
    if isinstance(value, str):
        return {"type": "str", "length": len(value)}
    return {"type": type(value).__name__}


def _to_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {}
    data: dict[str, Any] = {}
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_tokens_details",
        "completion_tokens_details",
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "cached_tokens",
        "cache_read_tokens",
        "cache_write_tokens",
        "cache_creation_input_tokens",
    ):
        if hasattr(value, key):
            data[key] = getattr(value, key)
    return data


def _first_int(*values: Any) -> int | None:
    for value in values:
        parsed = _int_or_none(value)
        if parsed is not None:
            return parsed
    return None


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return _sha256_text(encoded)
