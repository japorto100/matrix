# StreamingPacket types + SSE emitter — Phase 22g
# Onyx-pattern: type-safe SSE statt freiem JSON
# Protocol: Vercel AI Data Stream Protocol (text/event-stream)

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

# ── Packet types ─────────────────────────────────────────────────────────────
#
# Wire-format: Vercel AI SDK v6 Data Stream Protocol. The shapes below are
# the ones @ai-sdk/react's Zod union accepts. Historical notes:
#   - ThreadIdPacket (type "thread-id") is AI-SDK-incompatible; kept as a
#     hidden alias for the scheduler's runner_adapter which still reads it
#     off the wire from old generators. New emitters should produce
#     StartPacket + MessageMetaPacket({"threadId": ...}).
#   - Type names with hyphen-order swapped (step-start → start-step) and
#     renames (tool-start → tool-input-start, tool-result →
#     tool-output-available, tool-error → tool-output-error) are required for
#     v6 — the v5 names are silently dropped by the frontend parser.


@dataclass
class StartPacket:
    """AI-SDK v6 'start' — required first packet of a message. The messageId
    field is how we surface the agent's thread/message id to the frontend."""

    message_id: str = "m1"
    type: Literal["start"] = "start"


@dataclass
class ThreadIdPacket:
    """DEPRECATED: emit StartPacket + MessageMetaPacket({"threadId": ...})
    instead. Kept here for the scheduler's runner_adapter wire-format."""

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
    """AI-SDK v6 'tool-input-start' — a tool call has begun emitting."""

    tool_name: str
    tool_call_id: str
    type: Literal["tool-input-start"] = "tool-input-start"


@dataclass
class ToolResultPacket:
    """AI-SDK v6 'tool-output-available' — tool has returned a result."""

    tool_call_id: str
    output: dict
    type: Literal["tool-output-available"] = "tool-output-available"


@dataclass
class ToolErrorPacket:
    """AI-SDK v6 'tool-output-error'."""

    tool_call_id: str
    error_text: str
    type: Literal["tool-output-error"] = "tool-output-error"


@dataclass
class StepStartPacket:
    """AI-SDK v6 'start-step' (hyphen order matters)."""

    type: Literal["start-step"] = "start-step"


@dataclass
class StepFinishPacket:
    """AI-SDK v6 'finish-step'."""

    type: Literal["finish-step"] = "finish-step"


@dataclass
class ReasoningDeltaPacket:
    """Reasoning/thinking content delta (AI SDK ReasoningUIPart)."""

    delta: str
    id: str = "r1"
    type: Literal["reasoning-delta"] = "reasoning-delta"


@dataclass
class MessageMetaPacket:
    """AI-SDK v6 'message-metadata' — the field name is `messageMetadata`
    (emitted after snake→camel conversion from `message_metadata`)."""

    message_metadata: dict  # {promptTokens, completionTokens, threadId, ...}
    type: Literal["message-metadata"] = "message-metadata"


@dataclass
class FinishPacket:
    finish_reason: str = "stop"
    type: Literal["finish"] = "finish"


@dataclass
class ErrorPacket:
    """AI-SDK v6 'error' — the frontend zod union expects `errorText`."""

    error_text: str
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
        error_text=message,
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


# ── A2UI Ansatz X packets (plan-v2 Phase-2 #32/#34) ──────────────────────────
#
# Native packet types for streaming A2UI widget-surfaces over the same SSE
# channel as text/tool deltas. Ansatz X (SOTA, first-class) supersedes the
# dict-envelope "Ansatz Y" that ships the surface as a tool-result payload.
#
# Wire type names use the ``data-`` prefix so AI SDK v6's DefaultChatTransport
# treats them as project-specific data parts and forwards them to useChat's
# onData() callback instead of rejecting them against its built-in zod union.
# (Without the prefix, ai-sdk v6 aborts the stream on unrecognized types.)
#
# Lifecycle per surface:
#   1. A2uiSurfaceStartPacket   — declare new surface + initial data model
#   2. A2uiSurfaceUpdatePacket  — incremental component-tree edits (optional)
#   3. A2uiUpdateDataModelPacket — push new data bound into existing tree
#   4. A2uiSurfaceEndPacket     — complete, frontend may seal the surface
#
# A2uiDeleteSurfacePacket is a one-shot: removes a surface from the client.


@dataclass
class A2uiSurfaceStartPacket:
    """Open an A2UI surface and seed it with components + initial data model.

    ``components`` is the A2UI widget-tree (basicCatalog v0.9 + Chart
    extension in this project). ``data_model`` carries the initial bind
    values; live-updates arrive via A2uiUpdateDataModelPacket.
    """

    surface_id: str
    components: list | dict
    data_model: dict
    type: Literal["data-a2ui-surface-start"] = "data-a2ui-surface-start"


@dataclass
class A2uiSurfaceUpdatePacket:
    """Incremental component-tree update — agent may patch the shape of a
    surface without re-sending the whole tree. ``patch`` is a JSON-Patch
    (RFC 6902) array scoped to ``components``."""

    surface_id: str
    patch: list
    type: Literal["data-a2ui-update-components"] = "data-a2ui-update-components"


@dataclass
class A2uiUpdateDataModelPacket:
    """Push new data bound into an already-rendered surface. ``patch`` is a
    JSON-Patch array scoped to ``data_model`` (e.g. ticker updates, form
    field overwrites, list appends)."""

    surface_id: str
    patch: list
    type: Literal["data-a2ui-update-data-model"] = "data-a2ui-update-data-model"


@dataclass
class A2uiSurfaceEndPacket:
    """Signal that the agent is done streaming updates to this surface.
    Client may detach streaming-specific handlers after receiving."""

    surface_id: str
    type: Literal["data-a2ui-surface-end"] = "data-a2ui-surface-end"


@dataclass
class A2uiDeleteSurfacePacket:
    """Remove a surface from the client. Idempotent: client ignores if the
    surface isn't currently rendered."""

    surface_id: str
    type: Literal["data-a2ui-delete-surface"] = "data-a2ui-delete-surface"


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
