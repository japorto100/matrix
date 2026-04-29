"""Bounded MCP tool-call execution primitives.

The gateway owns MCP-specific timeout, cancellation and output-shaping before
results enter the provider-facing agent message loop.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Any

McpToolInvoker = Callable[["McpToolCallRequest"], Any | Awaitable[Any]]


@dataclass(frozen=True)
class McpGatewayExecutionConfig:
    timeout_seconds: float = 30.0
    max_output_bytes: int = 64 * 1024
    convert_cancellations: bool = True


@dataclass(frozen=True)
class McpToolCallRequest:
    tool_call_id: str
    matrix_name: str
    tool_input: dict[str, Any]
    session_id: str = ""
    audit_ref: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class McpGatewayExecutionResult:
    tool_call_id: str
    matrix_name: str
    ok: bool
    content: str
    elapsed_ms: int
    truncated: bool = False
    error: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_tool_message(self) -> dict[str, str]:
        """Return an OpenAI-compatible tool message preserving tool_call_id."""

        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "tool_use_id": self.tool_call_id,
            "content": self.content,
        }


async def execute_mcp_tool_call(
    request: McpToolCallRequest,
    invoke: McpToolInvoker,
    *,
    config: McpGatewayExecutionConfig | None = None,
) -> McpGatewayExecutionResult:
    """Run one MCP call with timeout and structured provider-facing output."""

    cfg = config or McpGatewayExecutionConfig()
    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            _call_invoker(invoke, request),
            timeout=max(cfg.timeout_seconds, 0.001),
        )
    except TimeoutError:
        return _failure_result(
            request,
            started=started,
            error_type="timeout",
            message=f"MCP tool timed out after {cfg.timeout_seconds:.3g}s",
            config=cfg,
        )
    except asyncio.CancelledError:
        if not cfg.convert_cancellations:
            raise
        return _failure_result(
            request,
            started=started,
            error_type="cancelled",
            message="MCP tool call was cancelled",
            config=cfg,
        )
    except Exception as exc:  # noqa: BLE001
        return _failure_result(
            request,
            started=started,
            error_type=exc.__class__.__name__,
            message=str(exc),
            config=cfg,
        )

    content, truncated = _bounded_json(
        {
            "ok": True,
            "tool_call_id": request.tool_call_id,
            "matrix_name": request.matrix_name,
            "result": result,
        },
        max_output_bytes=cfg.max_output_bytes,
    )
    return McpGatewayExecutionResult(
        tool_call_id=request.tool_call_id,
        matrix_name=request.matrix_name,
        ok=True,
        content=content,
        elapsed_ms=_elapsed_ms(started),
        truncated=truncated,
        error=None,
    )


async def _call_invoker(
    invoke: McpToolInvoker,
    request: McpToolCallRequest,
) -> Any:
    result = invoke(request)
    if inspect.isawaitable(result):
        return await result
    return result


def _failure_result(
    request: McpToolCallRequest,
    *,
    started: float,
    error_type: str,
    message: str,
    config: McpGatewayExecutionConfig,
) -> McpGatewayExecutionResult:
    error = {
        "type": error_type,
        "message": message,
        "tool_call_id": request.tool_call_id,
        "matrix_name": request.matrix_name,
    }
    content, truncated = _bounded_json(
        {"ok": False, "error": error},
        max_output_bytes=config.max_output_bytes,
    )
    return McpGatewayExecutionResult(
        tool_call_id=request.tool_call_id,
        matrix_name=request.matrix_name,
        ok=False,
        content=content,
        elapsed_ms=_elapsed_ms(started),
        truncated=truncated,
        error=error,
    )


def _bounded_json(payload: dict[str, Any], *, max_output_bytes: int) -> tuple[str, bool]:
    limit = max(max_output_bytes, 128)
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    encoded = content.encode("utf-8")
    if len(encoded) <= limit:
        return content, False

    preview_limit = max(limit - 192, 16)
    preview = encoded[:preview_limit].decode("utf-8", errors="replace")
    truncated_payload = {
        "ok": payload.get("ok", False),
        "truncated": True,
        "original_bytes": len(encoded),
        "max_output_bytes": limit,
        "preview": preview,
    }
    return json.dumps(truncated_payload, ensure_ascii=False, sort_keys=True), True


def _elapsed_ms(started: float) -> int:
    return max(int((time.perf_counter() - started) * 1000), 0)
