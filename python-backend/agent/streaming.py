# StreamingPacket types + SSE emitter — Phase 22g
# Onyx-pattern: type-safe SSE statt freiem JSON
# Protocol: Vercel AI Data Stream Protocol (text/event-stream)

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

# ── Packet types ─────────────────────────────────────────────────────────────


@dataclass
class ThreadIdPacket:
    thread_id: str
    type: Literal["thread-id"] = "thread-id"


@dataclass
class TextStartPacket:
    id: str = "t1"
    type: Literal["text-start"] = "text-start"


@dataclass
class TextDeltaPacket:
    delta: str
    id: str = "t1"
    type: Literal["text-delta"] = "text-delta"


@dataclass
class TextEndPacket:
    id: str = "t1"
    type: Literal["text-end"] = "text-end"


@dataclass
class ToolStartPacket:
    tool_name: str
    tool_call_id: str
    type: Literal["tool-start"] = "tool-start"


@dataclass
class ToolResultPacket:
    tool_call_id: str
    result: dict
    type: Literal["tool-result"] = "tool-result"


@dataclass
class ToolErrorPacket:
    tool_call_id: str
    error: str
    type: Literal["tool-error"] = "tool-error"


@dataclass
class StepStartPacket:
    """Marks a step boundary in multi-step agent execution (AI SDK StepStartUIPart)."""

    type: Literal["step-start"] = "step-start"


@dataclass
class ReasoningDeltaPacket:
    """Reasoning/thinking content delta (AI SDK ReasoningUIPart)."""

    delta: str
    type: Literal["reasoning-delta"] = "reasoning-delta"


@dataclass
class MessageMetaPacket:
    metadata: dict  # {promptTokens, completionTokens, threadId}
    type: Literal["message-metadata"] = "message-metadata"


@dataclass
class FinishPacket:
    finish_reason: str = "stop"
    type: Literal["finish"] = "finish"


@dataclass
class ErrorPacket:
    error: str
    type: Literal["error"] = "error"
    # Optional — populated by build_error_packet_with_failover() via the
    # resilience.error_classifier. Default None keeps existing callers and
    # the SSE/frontend consumers backwards-compatible (they just see an
    # extra `metadata` key when present).
    metadata: dict | None = None


def build_error_packet_with_failover(exc: BaseException, prefix: str = "") -> ErrorPacket:
    """Build an ErrorPacket whose ``metadata`` carries failover taxonomy info.

    Telemetry-only for Phase-1 wiring (runner/refiner): downstream consumers
    can read ``packet.metadata["failover_reason"]`` /
    ``["recovery_strategy"]`` / ``["retryable"]`` for UI hints and harness
    analysis, but the classifier does not gate retry here — that belongs to
    exec-16 Provider-Fallback-Chain.
    """
    from agent.resilience.error_classifier import classify_error

    result = classify_error(exc)
    message = f"{prefix}{exc}" if prefix else str(exc)
    return ErrorPacket(
        error=message,
        metadata={
            "failover_reason": result.reason.value,
            "recovery_strategy": result.recovery.value,
            "retryable": result.retryable,
            "status_code": result.status_code,
        },
    )


@dataclass
class ApprovalRequestPacket:
    """ABP.3: signals that a tool call needs human approval before execution."""

    tool_call_id: str
    tool_name: str
    tool_input: dict
    type: Literal["approval-request"] = "approval-request"


# ── SSE helper ────────────────────────────────────────────────────────────────


def _snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _to_sse(packet: object) -> str:
    """Serialize any packet dataclass to SSE data line (camelCase keys for frontend)."""
    if isinstance(packet, dict):
        data = packet
    else:
        data = {_snake_to_camel(k): v for k, v in asdict(packet).items()}  # type: ignore[arg-type]
    return f"data: {json.dumps(data)}\n\n"


# ── StreamEmitter ─────────────────────────────────────────────────────────────


class StreamEmitter:
    """Collects SSE strings emitted by the loop — callers async-iterate via __aiter__."""

    def __init__(self) -> None:
        self._queue: list[str] = []

    def emit(self, packet: object) -> None:
        self._queue.append(_to_sse(packet))

    def drain(self) -> list[str]:
        items, self._queue = self._queue, []
        return items


def sse(packet: object) -> str:
    """Standalone helper — returns a single SSE line string."""
    return _to_sse(packet)
