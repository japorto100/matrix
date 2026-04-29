"""Control Surface - Agent Ops Room read model and event stream."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from agent.control.request_scope import ensure_user_scope

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "ops"])

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
MEMORY_ACTION_TERMS = ("memory", "retain", "recall")
RAG_ACTION_TERMS = ("rag", "retrieval", "vector", "semantic")
KG_ACTION_TERMS = ("kg", "graph", "claim")
APPROVAL_ACTION_TERMS = ("approval", "consent", "human")


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


@router.get("/ops/events")
async def list_ops_events(
    request: Request,
    user_id: str | None = None,
    agent: str | None = None,
    session: str | None = None,
    tool: str | None = None,
    risk: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Return redacted ops events derived from audit and session state."""

    scope = ensure_user_scope(request, user_id)
    try:
        audit_events = _query_audit_events(scope.user_id, limit=limit, offset=offset)
        sessions = _query_sessions(limit=limit)
        tools = _query_tool_risks()
    except Exception as exc:  # noqa: BLE001
        logger.warning("list_ops_events failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"ops/events: {exc}") from exc

    return build_ops_read_model(
        audit_events=audit_events,
        sessions=sessions,
        tool_risks=tools,
        filters={
            "agent": agent,
            "session": session,
            "tool": tool,
            "risk": risk,
            "status": status,
        },
        limit=limit,
        offset=offset,
    )


@router.get("/ops/stream")
async def stream_ops_events(
    request: Request,
    user_id: str | None = None,
    interval_s: float = Query(default=5.0, ge=1.0, le=60.0),
) -> StreamingResponse:
    """SSE stream using the same redacted event contract as `/ops/events`."""

    scope = ensure_user_scope(request, user_id)

    async def _events() -> Iterable[str]:
        while True:
            try:
                payload = build_ops_read_model(
                    audit_events=_query_audit_events(scope.user_id, limit=100, offset=0),
                    sessions=_query_sessions(limit=100),
                    tool_risks=_query_tool_risks(),
                )
                yield f"event: ops_snapshot\ndata: {json.dumps(payload, default=str)}\n\n"
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                error = {"error": str(exc)[:200], "timestamp": _now_iso()}
                yield f"event: ops_error\ndata: {json.dumps(error)}\n\n"
            await asyncio.sleep(interval_s)

    return StreamingResponse(_events(), media_type="text/event-stream")


def build_ops_read_model(
    *,
    audit_events: Iterable[dict[str, Any]],
    sessions: Iterable[dict[str, Any]],
    tool_risks: dict[str, dict[str, Any]] | None = None,
    filters: dict[str, str | None] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Build the Feature 029 ops read model from existing trace/audit data."""

    risk_lookup = tool_risks or {}
    events = [
        audit_event_to_ops_event(event, risk_lookup.get(str(event.get("tool_name") or "")))
        for event in audit_events
    ]
    filtered_events = _apply_ops_filters(events, filters or {})
    session_rows = [
        _session_to_ops_session(session, filtered_events)
        for session in sessions
        if _session_matches(session, filters or {})
    ]
    blockers = [event for event in filtered_events if event["status"] in {"blocked", "failed"}]
    approvals = [
        event
        for event in filtered_events
        if event["status"] == "needs_approval" or event.get("approval_ref")
    ]
    return {
        "items": filtered_events,
        "sessions": session_rows,
        "blockers": blockers,
        "approvals": approvals,
        "filters": {key: value for key, value in (filters or {}).items() if value},
        "summary": {
            "total_events": len(filtered_events),
            "sessions": len(session_rows),
            "tool_events": sum(1 for event in filtered_events if event.get("tool_name")),
            "blockers": len(blockers),
            "approvals": len(approvals),
            "generated_at": _now_iso(),
        },
        "limit": limit,
        "offset": offset,
        "contract": "agent-ops-event/v1",
    }


def audit_event_to_ops_event(
    event: dict[str, Any],
    tool_risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert an audit row into a redacted AgentOpsEvent."""

    action = str(event.get("action") or "")
    metadata = _as_dict(event.get("metadata"))
    status = _derive_status(event)
    tool_name = str(event.get("tool_name") or "")
    return {
        "id": f"audit:{event.get('id')}",
        "source": "audit",
        "event_type": _event_type(action, tool_name),
        "status": status,
        "timestamp": _iso(event.get("timestamp")),
        "thread_id": event.get("thread_id") or "",
        "user_id": event.get("user_id") or "",
        "agent_role": event.get("agent_role") or event.get("agent_class") or "",
        "tool_name": tool_name,
        "action": action,
        "success": bool(event.get("success", True)),
        "risk": _tool_risk(tool_risk),
        "approval_ref": _approval_ref(metadata),
        "audit_ref": str(event.get("id") or ""),
        "duration_ms": event.get("duration_ms"),
        "error": str(event.get("error") or "")[:500],
        "input": redact_payload(event.get("input")),
        "output": redact_payload(event.get("output")),
        "metadata": redact_payload(metadata),
    }


def redact_payload(value: Any) -> Any:
    """Redact secrets before ops events reach the frontend."""

    if isinstance(value, str):
        return value if len(value) <= 600 else f"{value[:600]}...[truncated]"
    if isinstance(value, list):
        return [redact_payload(item) for item in value[:50]]
    if isinstance(value, tuple):
        return [redact_payload(item) for item in value[:50]]
    if not isinstance(value, dict):
        return value
    redacted: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        if any(part in key_text.lower() for part in SENSITIVE_KEY_PARTS):
            redacted[key_text] = "[redacted]"
        else:
            redacted[key_text] = redact_payload(item)
    return redacted


def _derive_status(event: dict[str, Any]) -> str:
    action = str(event.get("action") or "").lower()
    if event.get("success") is False:
        return "blocked"
    if any(term in action for term in APPROVAL_ACTION_TERMS):
        return "needs_approval"
    if event.get("tool_name"):
        return "active"
    return "waiting"


def _event_type(action: str, tool_name: str) -> str:
    text = f"{action} {tool_name}".lower()
    if any(term in text for term in MEMORY_ACTION_TERMS):
        return "memory"
    if any(term in text for term in RAG_ACTION_TERMS):
        return "rag"
    if any(term in text for term in KG_ACTION_TERMS):
        return "kg"
    if any(term in text for term in APPROVAL_ACTION_TERMS):
        return "approval"
    if tool_name:
        return "tool_call"
    return "trace"


def _apply_ops_filters(
    events: list[dict[str, Any]],
    filters: dict[str, str | None],
) -> list[dict[str, Any]]:
    out = events
    if filters.get("agent"):
        out = [event for event in out if event.get("agent_role") == filters["agent"]]
    if filters.get("session"):
        out = [event for event in out if event.get("thread_id") == filters["session"]]
    if filters.get("tool"):
        out = [event for event in out if event.get("tool_name") == filters["tool"]]
    if filters.get("risk"):
        out = [event for event in out if event.get("risk") == filters["risk"]]
    if filters.get("status"):
        out = [event for event in out if event.get("status") == filters["status"]]
    return sorted(out, key=lambda event: str(event.get("timestamp") or ""), reverse=True)


def _session_matches(
    session: dict[str, Any],
    filters: dict[str, str | None],
) -> bool:
    if filters.get("session") and session.get("thread_id") != filters["session"]:
        return False
    if filters.get("agent") and session.get("role") != filters["agent"]:
        return False
    return True


def _session_to_ops_session(
    session: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    thread_id = str(session.get("thread_id") or "")
    session_events = [event for event in events if event.get("thread_id") == thread_id]
    if any(event["status"] == "blocked" for event in session_events):
        status = "blocked"
    elif session.get("is_active"):
        status = "active"
    elif any(event["status"] == "needs_approval" for event in session_events):
        status = "needs_approval"
    elif session_events:
        status = "waiting"
    else:
        status = "replay"
    return {
        "thread_id": thread_id,
        "status": status,
        "agent_role": session.get("role") or "",
        "last_checkpoint": session.get("last_checkpoint"),
        "checkpoint_count": int(session.get("checkpoint_count") or 0),
        "event_count": len(session_events),
        "tool_count": sum(1 for event in session_events if event.get("tool_name")),
    }


def _query_audit_events(user_id: str, *, limit: int, offset: int) -> list[dict[str, Any]]:
    with psycopg.connect(_db_url(), autocommit=True) as conn:
        cur = conn.execute(
            """
            SELECT id, timestamp, action, user_id, thread_id, agent_class,
                   agent_role, tool_name, input, output, duration_ms,
                   success, error, metadata
            FROM agent.audit_events
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )
        cols = [d[0] for d in cur.description] if cur.description else []
        return [_row_to_dict(row, cols) for row in cur.fetchall()]


def _query_sessions(*, limit: int) -> list[dict[str, Any]]:
    with psycopg.connect(_db_url(), autocommit=True) as conn:
        if not _table_exists(conn, "public", "checkpoints"):
            return []
        cur = conn.execute(
            """
            SELECT thread_id, MAX(checkpoint_id) AS last_checkpoint, COUNT(*) AS checkpoint_count
            FROM checkpoints
            GROUP BY thread_id
            ORDER BY MAX(checkpoint_id) DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [
            {
                "thread_id": row[0],
                "last_checkpoint": str(row[1]) if row[1] else None,
                "checkpoint_count": int(row[2]),
                "is_active": False,
            }
            for row in cur.fetchall()
        ]


def _query_tool_risks() -> dict[str, dict[str, Any]]:
    try:
        from agent.tools.catalog import builtin_tool_catalog
        from agent.tools.registry import ToolRegistry

        return {
            item.name: {
                "risk": item.risk,
                "approval": item.approval,
                "group": item.group,
            }
            for item in builtin_tool_catalog(ToolRegistry.load().all())
        }
    except Exception:  # noqa: BLE001
        return {}


def _table_exists(conn: psycopg.Connection, schema: str, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (schema, table),
    ).fetchone()
    return row is not None


def _row_to_dict(row: Any, cols: list[str]) -> dict[str, Any]:
    data = dict(zip(cols, row, strict=True))
    for field in ("input", "output", "metadata"):
        data[field] = _as_dict(data.get(field))
    if data.get("timestamp"):
        data["timestamp"] = _iso(data["timestamp"])
    return data


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _tool_risk(tool_risk: dict[str, Any] | None) -> str:
    risk = str((tool_risk or {}).get("risk") or "unrated").lower()
    return risk if risk in {"low", "medium", "high", "critical", "unrated"} else "unrated"


def _approval_ref(metadata: dict[str, Any]) -> str:
    for key in ("approval_id", "approval_ref", "consent_id", "consent_ref"):
        value = metadata.get(key)
        if value:
            return str(value)
    return ""


def _iso(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value or _now_iso())


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
