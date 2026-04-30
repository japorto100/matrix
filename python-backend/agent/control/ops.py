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
MATRIX_ACTION_TERMS = (
    "matrix",
    "appservice",
    "bridge",
    "nats",
    "e2ee",
    "xsign",
    "cross-sign",
    "bootstrap",
    "mention",
    "reaction",
    "thread",
    "echo",
    "reconnect",
    "pairing",
)
MATRIX_BLOCKER_KEYS = (
    "matrix_blocker",
    "blocker_reason",
    "transport_blocker",
    "session_blocker",
)


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
    runtime_events = _runtime_events_from_ops_events(filtered_events)
    subagent_runs = _subagent_runs_from_runtime_events(runtime_events)
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
        "runtime_events": runtime_events,
        "runtime_summary": _runtime_summary(runtime_events),
        "subagent_runs": subagent_runs,
        "filters": {key: value for key, value in (filters or {}).items() if value},
        "summary": {
            "total_events": len(filtered_events),
            "sessions": len(session_rows),
            "tool_events": sum(1 for event in filtered_events if event.get("tool_name")),
            "blockers": len(blockers),
            "approvals": len(approvals),
            "runtime_events": len(runtime_events),
            "subagent_runs": len(subagent_runs),
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
    runtime_events = _runtime_events_from_metadata(metadata, event)
    status = _derive_status(event)
    tool_name = str(event.get("tool_name") or "")
    blocker_reason = _matrix_blocker_reason(metadata, action)
    linked_surfaces = _linked_surfaces(
        event=event,
        metadata=metadata,
        runtime_events=runtime_events,
    )
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
        "request_telemetry": redact_payload(metadata.get("request_telemetry") or {}),
        "linked_surfaces": linked_surfaces,
        "runtime_events": runtime_events,
        "runtime_event_count": len(runtime_events),
        "blocker_reason": blocker_reason,
        "matrix_room_id": _metadata_text(metadata, "matrix_room_id", "room_id"),
        "matrix_event_id": _metadata_text(metadata, "matrix_event_id", "event_id"),
        "matrix_thread_id": _metadata_text(
            metadata, "matrix_thread_id", "thread_root", "thread_id"
        ),
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
    metadata = _as_dict(event.get("metadata"))
    blocker_reason = _matrix_blocker_reason(metadata, action)
    if blocker_reason == "approval_reaction_wait":
        return "needs_approval"
    if blocker_reason:
        return "blocked"
    if event.get("success") is False:
        return "blocked"
    if any(term in action for term in APPROVAL_ACTION_TERMS):
        return "needs_approval"
    if event.get("tool_name"):
        return "active"
    return "waiting"


def _event_type(action: str, tool_name: str) -> str:
    text = f"{action} {tool_name}".lower()
    if any(term in text for term in MATRIX_ACTION_TERMS):
        return "matrix_transport"
    if "llm" in text or "request_telemetry" in text:
        return "llm"
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


def _matrix_blocker_reason(metadata: dict[str, Any], action: str = "") -> str:
    for key in MATRIX_BLOCKER_KEYS:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value
    text = f"{action} {json.dumps(metadata, default=str)}".lower()
    if "approval" in text and "reaction" in text and "wait" in text:
        return "approval_reaction_wait"
    if "echo" in text and ("loop" in text or "blocked" in text):
        return "echo_loop_blocked"
    if "mention" in text and ("required" in text or "gate" in text):
        return "mention_required"
    if "free" in text and "response" in text and "room" in text:
        return "free_response_room"
    if "reconnect" in text or "replay" in text:
        return "reconnect_replay"
    if "xsign" in text or "cross-sign" in text:
        return "xsign_bootstrap_required"
    if "e2ee" in text and "bootstrap" in text:
        return "e2ee_bootstrap_required"
    if "malformed" in text and "thread" in text:
        return "malformed_thread_reply"
    return ""


def _metadata_text(metadata: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(metadata.get(key) or "").strip()
        if value:
            return value
    return ""


def _runtime_events_from_metadata(
    metadata: dict[str, Any],
    audit_event: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    raw_items: list[Any] = []
    for key in ("runtime_events", "runtimeEvents"):
        value = metadata.get(key)
        if isinstance(value, list):
            raw_items.extend(value)
    for key in ("runtime_event", "runtimeEvent"):
        value = metadata.get(key)
        if value:
            raw_items.append(value)

    out: list[dict[str, Any]] = []
    for raw in raw_items[:50]:
        if not isinstance(raw, dict):
            continue
        event = redact_payload(raw)
        if not isinstance(event, dict):
            continue
        if audit_event and not event.get("thread_id"):
            event["thread_id"] = audit_event.get("thread_id") or ""
        if audit_event and not event.get("audit_ref"):
            event["audit_ref"] = str(audit_event.get("id") or "")
        out.append(event)
    return out


def _runtime_events_from_ops_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runtime_events: list[dict[str, Any]] = []
    for event in events:
        for runtime_event in event.get("runtime_events") or []:
            if isinstance(runtime_event, dict):
                runtime_events.append(runtime_event)
    return sorted(
        runtime_events,
        key=lambda item: str(item.get("timestamp") or ""),
        reverse=True,
    )


def _runtime_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_status: dict[str, int] = {}
    latest: dict[str, Any] | None = None
    for event in events:
        kind = str(event.get("kind") or "unknown")
        status = str(event.get("status") or "unknown")
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_status[status] = by_status.get(status, 0) + 1
        if latest is None or str(event.get("timestamp") or "") > str(latest.get("timestamp") or ""):
            latest = event
    return {
        "total": len(events),
        "by_kind": by_kind,
        "by_status": by_status,
        "latest": latest or {},
    }


def _subagent_runs_from_runtime_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if str(event.get("kind") or "") != "subagent":
            continue
        metadata = _as_dict(event.get("metadata"))
        key = (
            str(metadata.get("child_task_id") or "").strip()
            or str(event.get("audit_ref") or "").strip()
            or str(event.get("event_id") or "").strip()
        )
        if not key:
            continue
        grouped.setdefault(key, []).append(event)

    runs: list[dict[str, Any]] = []
    terminal_statuses = {"blocked", "failed", "completed", "stale", "cancelled"}
    for key, run_events in grouped.items():
        ordered = sorted(run_events, key=lambda item: str(item.get("timestamp") or ""))
        latest = ordered[-1]
        metadata = _as_dict(latest.get("metadata"))
        latest_status = str(latest.get("status") or "unknown")
        started_at = next(
            (
                str(event.get("timestamp") or "")
                for event in ordered
                if str(event.get("status") or "") in {"accepted", "started", "active"}
            ),
            str(ordered[0].get("timestamp") or ""),
        )
        ended_at = (
            str(latest.get("timestamp") or "")
            if latest_status in terminal_statuses
            else ""
        )
        runs.append(
            {
                "run_id": key,
                "child_task_id": str(metadata.get("child_task_id") or ""),
                "parent_thread_id": str(latest.get("thread_id") or ""),
                "role": str(metadata.get("role") or metadata.get("delegate_role") or ""),
                "delegate_kind": str(metadata.get("delegate_kind") or ""),
                "status": latest_status,
                "started_at": started_at,
                "ended_at": ended_at,
                "event_count": len(ordered),
                "spawn_depth": _safe_int(metadata.get("spawn_depth")),
                "next_spawn_depth": _safe_int(metadata.get("next_spawn_depth")),
                "max_spawn_depth": _safe_int(metadata.get("max_spawn_depth")),
                "last_event": latest,
                "controls": {
                    "status": "supported",
                    "kill": "unsupported",
                    "pause": "unsupported",
                    "replay": "unsupported",
                },
            }
        )
    return sorted(runs, key=lambda item: str(item.get("started_at") or ""), reverse=True)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list | tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _linked_surfaces(
    *,
    event: dict[str, Any],
    metadata: dict[str, Any],
    runtime_events: list[dict[str, Any]],
) -> dict[str, Any]:
    links: dict[str, Any] = {}
    telemetry = _as_dict(metadata.get("request_telemetry"))
    if telemetry:
        usage = _as_dict(telemetry.get("usage"))
        links["prompt_cache"] = {
            "surface": "prompt_cache",
            "label": "Prompt Cache",
            "href": _control_href("prompt-cache", "thread_id", event.get("thread_id")),
            "provider": str(telemetry.get("provider") or ""),
            "model": str(telemetry.get("model") or ""),
            "prompt_digest": str(telemetry.get("prompt_digest") or ""),
            "prompt_layout_digest": str(telemetry.get("prompt_layout_digest") or ""),
            "tool_catalog_digest": str(telemetry.get("tool_catalog_digest") or ""),
            "cache_read_tokens": usage.get("cache_read_tokens"),
            "cache_write_tokens": usage.get("cache_write_tokens"),
            "cache_break_reasons": _as_str_list(telemetry.get("cache_break_reasons")),
        }

    report_links = _report_artifact_links(event, metadata, runtime_events)
    if report_links:
        links["report_artifacts"] = report_links
    return links


def _control_href(tab: str, query_key: str, query_value: Any) -> str:
    value = str(query_value or "").strip()
    if not value:
        return f"/control/{tab}"
    from urllib.parse import quote

    return f"/control/{tab}?{query_key}={quote(value)}"


def _report_artifact_links(
    event: dict[str, Any],
    metadata: dict[str, Any],
    runtime_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for value in (
        metadata,
        event.get("input"),
        event.get("output"),
        *[_as_dict(item.get("metadata")) for item in runtime_events],
    ):
        candidates.extend(_find_report_artifact_refs(value))

    by_report_id: dict[str, dict[str, Any]] = {}
    for item in candidates:
        report_id = str(item.get("report_id") or "").strip()
        if not report_id:
            continue
        existing = by_report_id.setdefault(
            report_id,
            {
                "surface": "report_artifact",
                "label": f"Report {report_id}",
                "href": _control_href("reports", "report_id", report_id),
                "report_id": report_id,
                "manifest_path": "",
                "output_path": "",
                "status": "",
            },
        )
        for key in ("manifest_path", "output_path", "status"):
            if not existing.get(key) and item.get(key):
                existing[key] = str(item.get(key) or "")
    return list(by_report_id.values())[:8]


def _find_report_artifact_refs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []

    refs: list[dict[str, Any]] = []
    report_id = value.get("report_id") or value.get("reportId")
    if report_id:
        artifacts = _as_dict(value.get("artifacts"))
        refs.append(
            {
                "report_id": report_id,
                "manifest_path": (
                    value.get("manifest_path")
                    or value.get("manifest")
                    or artifacts.get("manifest")
                    or ""
                ),
                "output_path": (
                    value.get("output_path")
                    or value.get("html")
                    or artifacts.get("html")
                    or artifacts.get("text")
                    or ""
                ),
                "status": value.get("status") or value.get("validation_status") or "",
            }
        )

    for item in value.values():
        if isinstance(item, dict):
            refs.extend(_find_report_artifact_refs(item))
        elif isinstance(item, list):
            for nested in item[:20]:
                refs.extend(_find_report_artifact_refs(nested))
    return refs


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
