"""Control Surface — Sessions (LangGraph threads) (Slice 6 backend).

Queries langgraph_checkpoint_postgres internal tables for thread list.
The schema is public: `checkpoints (thread_id, checkpoint_ns, checkpoint_id,
parent_checkpoint_id, type, checkpoint, metadata, channel_values, ...)`.

Phase 1: raw SQL query. Phase 2: use langgraph's AsyncPostgresSaver.alist() API.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agent.control.request_scope import ensure_user_scope
from agent.runtime_events import make_runtime_event

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "sessions"])


class SessionControlRequest(BaseModel):
    confirm: bool = False
    reason: str = ""


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


def _now_ms() -> int:
    return int(time.time() * 1000)


def _table_exists(conn: psycopg.Connection, schema: str, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (schema, table),
    ).fetchone()
    return row is not None


def _session_control_event(
    *,
    operation: str,
    thread_id: str,
    status: str,
    summary: str,
    supported: bool,
    user_id: str = "",
    reason: str = "",
    outcome: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return make_runtime_event(
        kind="control",
        status=status,  # type: ignore[arg-type]
        name=f"session.{operation}.{outcome or status}",
        summary=summary,
        thread_id=thread_id,
        metadata={
            "operation": operation,
            "thread_id": thread_id,
            "user_id": user_id,
            "supported": supported,
            "reason": reason,
            "outcome": outcome or status,
            **(metadata or {}),
        },
    )


async def _audit_session_control(
    *,
    user_id: str,
    thread_id: str,
    operation: str,
    success: bool,
    runtime_event: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        from agent.audit.logger import AuditAction, audit_log

        await audit_log(
            action=AuditAction.ROUTE_DECISION,
            user_id=user_id,
            thread_id=thread_id,
            success=success,
            metadata={
                "control_action": f"session_{operation}",
                "runtime_events": [runtime_event],
                **(metadata or {}),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("session control audit failed: %s", exc)


def _session_status_snapshot(thread_id: str) -> dict[str, Any]:
    with psycopg.connect(_db_url(), autocommit=True) as conn:
        checkpoint_count = 0
        last_checkpoint = None
        if _table_exists(conn, "public", "checkpoints"):
            row = conn.execute(
                """
                SELECT MAX(checkpoint_id) AS last_checkpoint, COUNT(*) AS checkpoint_count
                FROM checkpoints
                WHERE thread_id = %s
                """,
                (thread_id,),
            ).fetchone()
            if row:
                last_checkpoint = str(row[0]) if row[0] else None
                checkpoint_count = int(row[1] or 0)

        session_rows: list[dict[str, Any]] = []
        if _table_exists(conn, "agent", "sessions"):
            cur = conn.execute(
                """
                SELECT session_id, session_type, status, started_at, completed_at,
                       updated_at, summary
                FROM agent.sessions
                WHERE thread_id = %s
                ORDER BY updated_at DESC NULLS LAST, started_at DESC NULLS LAST
                LIMIT 5
                """,
                (thread_id,),
            )
            cols = [d[0] for d in cur.description] if cur.description else []
            session_rows = [
                _row_to_public_session(dict(zip(cols, row, strict=True)))
                for row in cur.fetchall()
            ]

    active = any(row.get("status") == "active" for row in session_rows)
    status = "active" if active else ("replay" if checkpoint_count else "missing")
    return {
        "thread_id": thread_id,
        "status": status,
        "checkpoint_count": checkpoint_count,
        "last_checkpoint": last_checkpoint,
        "sessions": session_rows,
    }


def _row_to_public_session(row: dict[str, Any]) -> dict[str, Any]:
    summary = row.get("summary")
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except json.JSONDecodeError:
            summary = {}
    return {
        "session_id": str(row.get("session_id") or ""),
        "session_type": str(row.get("session_type") or ""),
        "status": str(row.get("status") or ""),
        "started_at": row.get("started_at"),
        "completed_at": row.get("completed_at"),
        "updated_at": row.get("updated_at"),
        "summary": summary if isinstance(summary, dict) else {},
    }


def _kill_session_rows(thread_id: str, *, reason: str, actor: str) -> dict[str, Any]:
    with psycopg.connect(_db_url(), autocommit=True) as conn:
        deleted = 0
        checkpoints_table_exists = _table_exists(conn, "public", "checkpoints")
        if checkpoints_table_exists:
            cur = conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,)
            )
            deleted = int(cur.rowcount or 0)

        updated_sessions: list[str] = []
        if _table_exists(conn, "agent", "sessions"):
            metadata = json.dumps(
                {
                    "control_action": "session_kill",
                    "killed_by": actor,
                    "kill_reason": reason,
                    "killed_at_ms": _now_ms(),
                }
            )
            cur = conn.execute(
                """
                UPDATE agent.sessions
                SET status = 'cancelled',
                    completed_at = COALESCE(completed_at, %s),
                    updated_at = %s,
                    metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                WHERE thread_id = %s
                RETURNING session_id
                """,
                (_now_ms(), _now_ms(), metadata, thread_id),
            )
            updated_sessions = [str(row[0]) for row in cur.fetchall()]

    return {
        "checkpoints_table_exists": checkpoints_table_exists,
        "deleted_checkpoints": deleted,
        "updated_sessions": updated_sessions,
    }


@router.get("/sessions")
async def list_sessions(
    active_only: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    """List LangGraph threads from checkpoints table."""
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            if not _table_exists(conn, "public", "checkpoints"):
                return {
                    "items": [],
                    "total": 0,
                    "note": "langgraph_checkpoint_postgres table 'checkpoints' not found — agent not yet run",
                }

            # Get distinct thread_ids with latest checkpoint
            cur = conn.execute(
                """
                SELECT
                    thread_id,
                    MAX(checkpoint_id) AS last_checkpoint,
                    COUNT(*) AS checkpoint_count
                FROM checkpoints
                GROUP BY thread_id
                ORDER BY MAX(checkpoint_id) DESC
                LIMIT %s
                """,
                (limit,),
            )
            [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
    except Exception as e:  # noqa: BLE001
        logger.warning("list_sessions failed: %s", e)
        return {"items": [], "total": 0, "error": str(e)[:200]}

    items = [
        {
            "thread_id": row[0],
            "last_checkpoint": str(row[1]) if row[1] else None,
            "checkpoint_count": int(row[2]),
            "is_active": False,  # TODO Phase 2: track live sessions via running agent runner
        }
        for row in rows
    ]
    return {"items": items, "total": len(items)}


@router.post("/sessions/{thread_id}/status")
async def session_status(
    thread_id: str,
    request: Request,
    user_id: str | None = None,
) -> dict[str, Any]:
    scope = ensure_user_scope(request, user_id)
    snapshot = _session_status_snapshot(thread_id)
    runtime_event = _session_control_event(
        operation="status",
        thread_id=thread_id,
        status="completed",
        summary=f"Session status is {snapshot['status']}",
        supported=True,
        user_id=scope.user_id,
        outcome=str(snapshot["status"]),
        metadata={"snapshot": snapshot},
    )
    await _audit_session_control(
        user_id=scope.user_id,
        thread_id=thread_id,
        operation="status",
        success=True,
        runtime_event=runtime_event,
    )
    return {
        "status": "supported",
        "operation": "status",
        "thread_id": thread_id,
        "snapshot": snapshot,
        "runtime_events": [runtime_event],
    }


@router.post("/sessions/{thread_id}/pause")
async def pause_session(
    thread_id: str,
    req: SessionControlRequest,
    request: Request,
    user_id: str | None = None,
) -> dict[str, Any]:
    scope = ensure_user_scope(request, user_id)
    runtime_event = _session_control_event(
        operation="pause",
        thread_id=thread_id,
        status="blocked",
        summary="Pause is not supported by the current backend runner",
        supported=False,
        user_id=scope.user_id,
        reason=req.reason,
        outcome="unsupported",
    )
    await _audit_session_control(
        user_id=scope.user_id,
        thread_id=thread_id,
        operation="pause",
        success=False,
        runtime_event=runtime_event,
    )
    return {
        "status": "unsupported",
        "operation": "pause",
        "thread_id": thread_id,
        "runtime_events": [runtime_event],
    }


@router.post("/sessions/{thread_id}/replay")
async def replay_session(
    thread_id: str,
    req: SessionControlRequest,
    request: Request,
    user_id: str | None = None,
) -> dict[str, Any]:
    scope = ensure_user_scope(request, user_id)
    runtime_event = _session_control_event(
        operation="replay",
        thread_id=thread_id,
        status="blocked",
        summary="Replay export is not yet supported by this endpoint",
        supported=False,
        user_id=scope.user_id,
        reason=req.reason,
        outcome="unsupported",
    )
    await _audit_session_control(
        user_id=scope.user_id,
        thread_id=thread_id,
        operation="replay",
        success=False,
        runtime_event=runtime_event,
    )
    return {
        "status": "unsupported",
        "operation": "replay",
        "thread_id": thread_id,
        "runtime_events": [runtime_event],
    }


@router.post("/sessions/{thread_id}/kill")
async def kill_session_control(
    thread_id: str,
    req: SessionControlRequest,
    request: Request,
    user_id: str | None = None,
) -> dict[str, Any]:
    scope = ensure_user_scope(request, user_id)
    if not req.confirm:
        runtime_event = _session_control_event(
            operation="kill",
            thread_id=thread_id,
            status="needs_approval",
            summary="Kill requires explicit confirmation",
            supported=True,
            user_id=scope.user_id,
            reason=req.reason,
            outcome="confirmation_required",
        )
        await _audit_session_control(
            user_id=scope.user_id,
            thread_id=thread_id,
            operation="kill",
            success=False,
            runtime_event=runtime_event,
        )
        return {
            "status": "confirmation_required",
            "operation": "kill",
            "thread_id": thread_id,
            "runtime_events": [runtime_event],
        }

    result = _kill_session_rows(thread_id, reason=req.reason, actor=scope.actor)
    runtime_event = _session_control_event(
        operation="kill",
        thread_id=thread_id,
        status="cancelled",
        summary="Session kill completed",
        supported=True,
        user_id=scope.user_id,
        reason=req.reason,
        outcome="killed",
        metadata=result,
    )
    await _audit_session_control(
        user_id=scope.user_id,
        thread_id=thread_id,
        operation="kill",
        success=True,
        runtime_event=runtime_event,
        metadata=result,
    )
    return {
        "status": "killed",
        "operation": "kill",
        "thread_id": thread_id,
        **result,
        "runtime_events": [runtime_event],
    }


@router.get("/sessions/{thread_id}")
async def get_session(thread_id: str) -> dict[str, Any]:
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            if not _table_exists(conn, "public", "checkpoints"):
                raise HTTPException(
                    status_code=404, detail="checkpoints table not found"
                )
            cur = conn.execute(
                """
                SELECT checkpoint_id, parent_checkpoint_id, metadata
                FROM checkpoints
                WHERE thread_id = %s
                ORDER BY checkpoint_id DESC
                LIMIT 10
                """,
                (thread_id,),
            )
            rows = cur.fetchall()
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"get session: {e}") from e

    if not rows:
        raise HTTPException(status_code=404, detail="Thread not found")

    checkpoints = [
        {
            "checkpoint_id": str(row[0]),
            "parent_checkpoint_id": str(row[1]) if row[1] else None,
            "metadata": json.loads(row[2])
            if isinstance(row[2], str)
            else (row[2] or {}),
        }
        for row in rows
    ]
    return {
        "thread_id": thread_id,
        "checkpoints": checkpoints,
        "count": len(checkpoints),
    }


@router.delete("/sessions/{thread_id}")
async def kill_session(thread_id: str) -> dict[str, Any]:
    """Delete all checkpoints for a thread (Dev Mode only, approval-write)."""
    try:
        result = _kill_session_rows(thread_id, reason="legacy_delete", actor="control")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"kill session: {e}") from e

    if not result["checkpoints_table_exists"] and not result["updated_sessions"]:
        return {"status": "no_table", "thread_id": thread_id, "deleted": 0}
    return {
        "status": "killed",
        "thread_id": thread_id,
        "deleted": result["deleted_checkpoints"],
        "updated_sessions": result["updated_sessions"],
    }
