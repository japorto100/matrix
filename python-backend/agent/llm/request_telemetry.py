"""Provider-agnostic request/cache telemetry helpers for LLM calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

REQUEST_TELEMETRY_CONTRACT = "provider-request-telemetry/v1"


@dataclass(frozen=True)
class UsageTelemetry:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
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
    thread_id: str
    iteration: int
    prompt_digest: str
    prompt_layout_digest: str
    tool_catalog_digest: str
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
) -> dict[str, Any]:
    """Build one redacted request telemetry envelope.

    Prompt text is never stored. `prompt_digest` hashes normalized content and
    `prompt_layout_digest` hashes role/content shape plus cache-control markers.
    """

    prompt_digest = digest_prompt(messages, include_text=True)
    layout_digest = digest_prompt(messages, include_text=False)
    tool_digest = digest_tool_catalog(tools)
    telemetry = RequestTelemetry(
        provider=provider,
        model=model,
        router=router,
        thread_id=thread_id,
        iteration=iteration,
        prompt_digest=prompt_digest,
        prompt_layout_digest=layout_digest,
        tool_catalog_digest=tool_digest,
        usage=normalize_usage(usage),
        cache_break_reasons=tuple(
            detect_cache_break(
                previous=previous,
                prompt_digest=prompt_digest,
                prompt_layout_digest=layout_digest,
                tool_catalog_digest=tool_digest,
                model=model,
            )
        ),
        metadata=metadata or {},
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

    unknown: list[str] = []
    if reasoning is None:
        unknown.append("reasoning_tokens")
    if cache_read is None:
        unknown.append("cache_read_tokens")
    if cache_write is None:
        unknown.append("cache_write_tokens")

    return UsageTelemetry(
        prompt_tokens=prompt,
        completion_tokens=completion,
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


def detect_cache_break(
    *,
    previous: dict[str, Any] | None,
    prompt_digest: str,
    prompt_layout_digest: str,
    tool_catalog_digest: str,
    model: str,
) -> list[str]:
    if not previous:
        return ["first_request"]
    reasons: list[str] = []
    if previous.get("model") != model:
        reasons.append("model_changed")
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
        "request_telemetry.prompt_digest": str(telemetry.get("prompt_digest") or ""),
        "request_telemetry.prompt_layout_digest": str(
            telemetry.get("prompt_layout_digest") or ""
        ),
        "request_telemetry.tool_catalog_digest": str(
            telemetry.get("tool_catalog_digest") or ""
        ),
        "request_telemetry.cache_break_reasons": ",".join(
            str(reason) for reason in telemetry.get("cache_break_reasons") or ()
        ),
    }
    for key in (
        "prompt_tokens",
        "completion_tokens",
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
