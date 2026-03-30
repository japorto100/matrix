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
    threadId: str
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
class MessageMetaPacket:
    metadata: dict  # {promptTokens, completionTokens, threadId}
    type: Literal["message-metadata"] = "message-metadata"


@dataclass
class FinishPacket:
    finishReason: str = "stop"
    type: Literal["finish"] = "finish"


@dataclass
class ErrorPacket:
    error: str
    type: Literal["error"] = "error"


@dataclass
class ApprovalRequestPacket:
    """ABP.3: signals that a tool call needs human approval before execution."""
    tool_call_id: str
    tool_name: str
    tool_input: dict
    type: Literal["approval-request"] = "approval-request"


# ── SSE helper ────────────────────────────────────────────────────────────────

def _to_sse(packet: object) -> str:
    """Serialize any packet dataclass to SSE data line."""
    if isinstance(packet, dict):
        data = packet
    else:
        data = asdict(packet)  # type: ignore[arg-type]
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
