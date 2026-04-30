"""Provider-agnostic runtime event contract for agent UI/control surfaces."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, get_args

RUNTIME_EVENT_CONTRACT = "agent-runtime-event/v1"
RUNTIME_EVENT_REDACTION_POLICY = "runtime-event-redaction/v1"

RuntimeEventKind = Literal[
    "run",
    "turn",
    "llm",
    "tool",
    "memory",
    "rag",
    "kg",
    "artifact",
    "subagent",
    "mcp",
    "matrix",
    "control",
]

RuntimeEventStatus = Literal[
    "accepted",
    "started",
    "active",
    "waiting",
    "needs_approval",
    "blocked",
    "failed",
    "completed",
    "stale",
    "cancelled",
]

RuntimeEventOutcome = Literal[
    "ok",
    "error",
    "timeout",
    "killed",
    "cancelled",
    "stale",
    "deferred",
]

RUNTIME_EVENT_KIND_DEFINITIONS: dict[RuntimeEventKind, dict[str, tuple[str, ...] | str]] = {
    "run": {
        "description": "Agent run lifecycle.",
        "name_prefixes": ("run.",),
    },
    "turn": {
        "description": "User/assistant turn lifecycle.",
        "name_prefixes": ("turn.",),
    },
    "llm": {
        "description": "Model request, response and provider-neutral recovery events.",
        "name_prefixes": ("llm.", "model."),
    },
    "tool": {
        "description": "Tool call start/result/failure events.",
        "name_prefixes": ("tool.",),
    },
    "memory": {
        "description": "Memory recall, retain, block and handoff events.",
        "name_prefixes": ("memory.",),
    },
    "rag": {
        "description": "Vector, lexical and fused retrieval events.",
        "name_prefixes": ("rag.", "retrieval."),
    },
    "kg": {
        "description": "KG claim selection, path and projection events.",
        "name_prefixes": ("kg.",),
    },
    "artifact": {
        "description": "Generated report/file/downstream artifact events.",
        "name_prefixes": ("artifact.", "report."),
    },
    "subagent": {
        "description": "Delegation/subagent lifecycle and parent handoff events.",
        "name_prefixes": ("subagent.", "a2a."),
    },
    "mcp": {
        "description": "MCP catalog, gateway and tool-descriptor lifecycle events.",
        "name_prefixes": ("mcp.",),
    },
    "matrix": {
        "description": "Matrix transport/session hygiene events.",
        "name_prefixes": ("matrix.",),
    },
    "control": {
        "description": "Control-plane operation, status and cache-impact events.",
        "name_prefixes": ("control.", "cache."),
    },
}

RUNTIME_EVENT_OUTCOME_BY_STATUS: dict[RuntimeEventStatus, RuntimeEventOutcome] = {
    "accepted": "deferred",
    "started": "deferred",
    "active": "deferred",
    "waiting": "deferred",
    "needs_approval": "deferred",
    "blocked": "deferred",
    "failed": "error",
    "completed": "ok",
    "stale": "stale",
    "cancelled": "cancelled",
}

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "cookie",
    "password",
    "secret",
    "token",
)


@dataclass(frozen=True)
class RuntimeEvent:
    kind: RuntimeEventKind
    status: RuntimeEventStatus
    name: str
    summary: str = ""
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex}")
    run_id: str = ""
    span_id: str = ""
    parent_id: str = ""
    parent_event_id: str = ""
    session_id: str = ""
    thread_id: str = ""
    turn: int = 0
    turn_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    redaction: dict[str, Any] = field(default_factory=dict)
    contract: str = RUNTIME_EVENT_CONTRACT

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["metadata"] = redact_runtime_payload(payload.get("metadata") or {})
        payload["payload"] = redact_runtime_payload(payload.get("payload") or {})
        payload["redaction"] = {
            "policy": RUNTIME_EVENT_REDACTION_POLICY,
            "applied": True,
            "max_string_chars": 800,
            "max_items": 80,
            **(payload.get("redaction") or {}),
        }
        return payload


def make_runtime_event(
    *,
    kind: RuntimeEventKind,
    status: RuntimeEventStatus,
    name: str,
    summary: str = "",
    event_id: str | None = None,
    run_id: str = "",
    span_id: str = "",
    parent_id: str = "",
    parent_event_id: str = "",
    session_id: str = "",
    thread_id: str = "",
    turn: int = 0,
    turn_id: str = "",
    metadata: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    outcome: RuntimeEventOutcome | None = None,
) -> dict[str, Any]:
    """Build a redacted runtime event dict for SSE, traces and read models."""

    resolved_event_id = event_id or f"evt_{uuid.uuid4().hex}"
    resolved_thread_id = str(thread_id or "")
    resolved_session_id = str(session_id or resolved_thread_id or "")
    resolved_run_id = str(run_id or resolved_session_id or resolved_thread_id or resolved_event_id)
    resolved_turn_id = str(
        turn_id
        or (
            f"{resolved_session_id}:turn:{turn}"
            if resolved_session_id and int(turn or 0) > 0
            else ""
        )
    )
    resolved_span_id = str(span_id or resolved_event_id)
    resolved_parent_id = str(parent_id or parent_event_id or "")
    resolved_metadata = _metadata_with_outcome(
        status=status,
        name=name,
        metadata=metadata or {},
        outcome=outcome,
    )
    return RuntimeEvent(
        kind=kind,
        status=status,
        name=name,
        summary=summary,
        event_id=resolved_event_id,
        run_id=resolved_run_id,
        span_id=resolved_span_id,
        parent_id=resolved_parent_id,
        parent_event_id=parent_event_id,
        session_id=resolved_session_id,
        thread_id=resolved_thread_id,
        turn=turn,
        turn_id=resolved_turn_id,
        metadata=resolved_metadata,
        payload=payload or {},
    ).to_dict()


def runtime_event_kind_definition(kind: RuntimeEventKind) -> dict[str, tuple[str, ...] | str]:
    """Return the provider-agnostic event-kind definition used by replay gates."""

    return RUNTIME_EVENT_KIND_DEFINITIONS[kind]


def runtime_event_name_matches_kind(*, kind: RuntimeEventKind, name: str) -> bool:
    """Check whether a runtime event name belongs to the declared kind."""

    prefixes = RUNTIME_EVENT_KIND_DEFINITIONS[kind]["name_prefixes"]
    return any(str(name).startswith(prefix) for prefix in prefixes)


def normalize_runtime_event_outcome(
    *, status: RuntimeEventStatus, name: str = "", metadata: dict[str, Any] | None = None
) -> RuntimeEventOutcome:
    """Map current event state to the stable replay outcome taxonomy."""

    source = metadata or {}
    explicit = source.get("outcome")
    if explicit in get_args(RuntimeEventOutcome):
        return explicit
    lowered_name = name.lower()
    error_type = str(source.get("error_type") or "").lower()
    reason = str(source.get("reason") or "").lower()
    if "timeout" in lowered_name or "timeout" in error_type or "timeout" in reason:
        return "timeout"
    if explicit == "killed" or "kill" in lowered_name or reason == "killed":
        return "killed"
    return RUNTIME_EVENT_OUTCOME_BY_STATUS[status]


def _metadata_with_outcome(
    *,
    status: RuntimeEventStatus,
    name: str,
    metadata: dict[str, Any],
    outcome: RuntimeEventOutcome | None,
) -> dict[str, Any]:
    resolved = dict(metadata)
    if outcome is not None:
        resolved["outcome"] = outcome
    else:
        resolved.setdefault(
            "outcome",
            normalize_runtime_event_outcome(
                status=status,
                name=name,
                metadata=resolved,
            ),
        )
    return resolved


def redact_runtime_payload(value: Any) -> Any:
    """Redact secrets and cap large payloads before UI/control exposure."""

    if isinstance(value, str):
        return value if len(value) <= 800 else f"{value[:800]}...[truncated]"
    if isinstance(value, list):
        return [redact_runtime_payload(item) for item in value[:80]]
    if isinstance(value, tuple):
        return [redact_runtime_payload(item) for item in value[:80]]
    if not isinstance(value, dict):
        return value
    redacted: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        if any(part in key_text.lower() for part in SENSITIVE_KEY_PARTS):
            redacted[key_text] = "[redacted]"
        else:
            redacted[key_text] = redact_runtime_payload(item)
    return redacted


def runtime_event_span_attributes(event: dict[str, Any]) -> dict[str, Any]:
    """Small OTel-safe attribute subset for one runtime event."""

    return {
        "runtime_event.contract": str(event.get("contract") or RUNTIME_EVENT_CONTRACT),
        "runtime_event.id": str(event.get("event_id") or ""),
        "runtime_event.run_id": str(event.get("run_id") or ""),
        "runtime_event.span_id": str(event.get("span_id") or ""),
        "runtime_event.kind": str(event.get("kind") or ""),
        "runtime_event.status": str(event.get("status") or ""),
        "runtime_event.name": str(event.get("name") or ""),
    }
