"""Control Surface — Audit Log Viewer (Slice 6 backend).

Queries agent.audit_events with flexible filters (action, user, role, date range).
Uses indexes from Migration 007_audit_indexes.py for performance.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request

from agent.control.request_scope import ensure_user_scope

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "audit"])

MCP_POLICY_AUDIT_ACTIONS = (
    "MCP_CATALOG_CHANGED",
    "MCP_DESCRIPTOR_DRIFT",
    "MCP_TOOL_DENIED",
    "MCP_RESOURCE_DENIED",
    "MCP_SESSION_GRANT_ISSUED",
)


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


def _row_to_event(row: Any, cols: list[str]) -> dict[str, Any]:
    r = dict(zip(cols, row, strict=True))
    for field in ("input", "output", "metadata"):
        val = r.get(field)
        if isinstance(val, str):
            try:
                r[field] = json.loads(val)
            except Exception:  # noqa: BLE001
                pass
    if r.get("timestamp"):
        r["timestamp"] = r["timestamp"].isoformat()
    return r


def _append_mcp_policy_audit_clause(
    clauses: list[str],
    params: list[Any],
) -> None:
    placeholders = ", ".join(["%s"] * len(MCP_POLICY_AUDIT_ACTIONS))
    clauses.append(
        "("
        f"action IN ({placeholders}) "
        "OR tool_name LIKE %s "
        "OR metadata::text ILIKE %s"
        ")"
    )
    params.extend([*MCP_POLICY_AUDIT_ACTIONS, "mcp_%", "%mcp%"])


def _audit_where(clauses: list[str]) -> str:
    return f"WHERE {' AND '.join(clauses)}" if clauses else ""


@router.get("/audit")
async def list_audit_events(
    request: Request,
    action: str | None = None,
    user_id: str | None = None,
    thread_id: str | None = None,
    role: str | None = None,
    tool_name: str | None = None,
    success: bool | None = None,
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Filtered audit events query."""
    scope = ensure_user_scope(request, user_id)
    user_id = scope.user_id
    clauses: list[str] = []
    params: list[Any] = []

    if action:
        clauses.append("action = %s")
        params.append(action)
    if user_id:
        clauses.append("user_id = %s")
        params.append(user_id)
    if thread_id:
        clauses.append("thread_id = %s")
        params.append(thread_id)
    if role:
        clauses.append("agent_role = %s")
        params.append(role)
    if tool_name:
        clauses.append("tool_name = %s")
        params.append(tool_name)
    if success is not None:
        clauses.append("success = %s")
        params.append(success)
    if from_date is not None:
        clauses.append("timestamp >= %s")
        params.append(from_date)
    if to_date is not None:
        clauses.append("timestamp <= %s")
        params.append(to_date)

    where = _audit_where(clauses)

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            # Get total
            count_cur = conn.execute(
                f"SELECT COUNT(*) FROM agent.audit_events {where}", tuple(params)
            )
            total_row = count_cur.fetchone()
            total = int(total_row[0]) if total_row else 0

            # Get page
            cur = conn.execute(
                f"""
                SELECT id, timestamp, action, user_id, thread_id, agent_class,
                       agent_role, tool_name, input, output, duration_ms,
                       success, error, metadata
                FROM agent.audit_events
                {where}
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
                """,
                tuple([*params, limit, offset]),
            )
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
    except Exception as e:  # noqa: BLE001
        logger.exception("list_audit_events failed")
        raise HTTPException(status_code=500, detail=f"audit: {e}") from e

    items = [_row_to_event(r, cols) for r in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/audit/mcp-policy")
async def list_mcp_policy_audit_events(
    request: Request,
    user_id: str | None = None,
    success: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Query MCP catalog changes, descriptor drift and call/resource denials."""

    scope = ensure_user_scope(request, user_id)
    clauses: list[str] = ["user_id = %s"]
    params: list[Any] = [scope.user_id]
    if success is not None:
        clauses.append("success = %s")
        params.append(success)
    _append_mcp_policy_audit_clause(clauses, params)
    where = _audit_where(clauses)

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            count_cur = conn.execute(
                f"SELECT COUNT(*) FROM agent.audit_events {where}", tuple(params)
            )
            total_row = count_cur.fetchone()
            total = int(total_row[0]) if total_row else 0

            cur = conn.execute(
                f"""
                SELECT id, timestamp, action, user_id, thread_id, agent_class,
                       agent_role, tool_name, input, output, duration_ms,
                       success, error, metadata
                FROM agent.audit_events
                {where}
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
                """,
                tuple([*params, limit, offset]),
            )
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
    except Exception as e:  # noqa: BLE001
        logger.exception("list_mcp_policy_audit_events failed")
        raise HTTPException(status_code=500, detail=f"audit/mcp-policy: {e}") from e

    items = [_row_to_event(r, cols) for r in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "actions": list(MCP_POLICY_AUDIT_ACTIONS),
    }


@router.get("/audit/{event_id}")
async def get_audit_event(event_id: int) -> dict[str, Any]:
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            cur = conn.execute(
                """
                SELECT id, timestamp, action, user_id, thread_id, agent_class,
                       agent_role, tool_name, input, output, duration_ms,
                       success, error, metadata
                FROM agent.audit_events
                WHERE id = %s
                """,
                (event_id,),
            )
            cols = [d[0] for d in cur.description] if cur.description else []
            row = cur.fetchone()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"audit: {e}") from e

    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return _row_to_event(row, cols)
