"""Control Surface — Sandbox Runs (Slice 5 backend).

Sandbox runs are already audited (exec-12) as action='SANDBOX_EXEC' in
agent.audit_events. We query that table directly — no separate sandbox_runs
table needed.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "sandbox"])


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


def _row_to_run(row: Any, cols: list[str]) -> dict[str, Any]:
    r = dict(zip(cols, row, strict=True))
    metadata = r.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:  # noqa: BLE001
            metadata = {}

    input_data = r.get("input") or {}
    if isinstance(input_data, str):
        try:
            input_data = json.loads(input_data)
        except Exception:  # noqa: BLE001
            input_data = {}

    return {
        "id": metadata.get("run_id") or str(r.get("id")),
        "audit_id": r.get("id"),
        "started_at": r["timestamp"].isoformat() if r.get("timestamp") else None,
        "user_id": r.get("user_id"),
        "role": r.get("agent_role"),
        "tool_name": r.get("tool_name"),
        "code_preview": (input_data.get("code") or input_data.get("script") or "")[
            :200
        ],
        "status": metadata.get("status")
        or ("failed" if not r.get("success") else "completed"),
        "duration_ms": r.get("duration_ms"),
        "exit_code": metadata.get("exit_code"),
        "stdout_preview": (metadata.get("stdout") or "")[:500],
        "stderr_preview": (r.get("error") or metadata.get("stderr") or "")[:500],
    }


@router.get("/sandbox/runs")
async def list_sandbox_runs(
    status: str | None = None,
    role: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """List recent sandbox runs from audit_events."""
    clauses = [
        "action IN ('SANDBOX_EXEC', 'SANDBOX_PYTHON', 'SANDBOX_BROWSER', 'SANDBOX_BASH')"
    ]
    params: list[Any] = []
    if role:
        clauses.append("agent_role = %s")
        params.append(role)

    where = "WHERE " + " AND ".join(clauses)
    params.append(int(limit))

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            cur = conn.execute(
                f"""
                SELECT id, timestamp, action, user_id, thread_id, agent_role,
                       tool_name, input, output, duration_ms, success, error, metadata
                FROM agent.audit_events
                {where}
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                tuple(params),
            )
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
    except Exception as e:  # noqa: BLE001
        logger.exception("list_sandbox_runs failed")
        raise HTTPException(status_code=500, detail=f"sandbox runs: {e}") from e

    items = [_row_to_run(r, cols) for r in rows]
    if status:
        items = [i for i in items if i["status"] == status]

    return {"items": items, "total": len(items)}


@router.get("/sandbox/runs/{run_id}")
async def get_sandbox_run(run_id: str) -> dict[str, Any]:
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            cur = conn.execute(
                """
                SELECT id, timestamp, action, user_id, thread_id, agent_role,
                       tool_name, input, output, duration_ms, success, error, metadata
                FROM agent.audit_events
                WHERE metadata::jsonb ->> 'run_id' = %s
                   OR id::text = %s
                LIMIT 1
                """,
                (run_id, run_id),
            )
            cols = [d[0] for d in cur.description] if cur.description else []
            row = cur.fetchone()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"sandbox run: {e}") from e

    if row is None:
        raise HTTPException(status_code=404, detail="Sandbox run not found")
    return _row_to_run(row, cols)
