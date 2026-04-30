"""Control Surface — A2A Delegations Log (Slice 6 backend).

Queries agent.a2a_delegations (Migration 006) for persistent delegation history.
A2A runtime persists accepted delegations when AUDIT_DB_URL or HINDSIGHT_DB_URL
is configured; local no-DB runs still return an empty/error-tolerant list.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "a2a"])


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


def _row_to_dict(row: Any, cols: list[str]) -> dict[str, Any]:
    r = dict(zip(cols, row, strict=True))
    if r.get("started_at"):
        r["started_at"] = r["started_at"].isoformat()
    if r.get("completed_at"):
        r["completed_at"] = r["completed_at"].isoformat()
    if r.get("id"):
        r["id"] = str(r["id"])
    if isinstance(r.get("result"), str):
        try:
            r["result"] = json.loads(r["result"])
        except Exception:  # noqa: BLE001
            pass
    # Frontend expects `result_preview` (short string)
    if isinstance(r.get("result"), dict):
        r["result_preview"] = str(r["result"])[:200]
    else:
        r["result_preview"] = None
    return r


@router.get("/a2a/delegations")
async def list_a2a_delegations(
    status: str | None = None,
    thread_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = %s")
        params.append(status)
    if thread_id:
        clauses.append("thread_id = %s")
        params.append(thread_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(int(limit))

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            cur = conn.execute(
                f"""
                SELECT id, from_role, to_role, task, status, started_at,
                       completed_at, result, thread_id, user_id
                FROM agent.a2a_delegations
                {where}
                ORDER BY started_at DESC
                LIMIT %s
                """,
                tuple(params),
            )
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall() or []
    except Exception as e:  # noqa: BLE001
        logger.warning("a2a list failed: %s", e)
        return {"items": [], "total": 0, "error": str(e)[:200]}

    items = [_row_to_dict(r, cols) for r in rows]
    return {"items": items, "total": len(items)}


@router.get("/a2a/delegations/{delegation_id}")
async def get_a2a_delegation(delegation_id: str) -> dict[str, Any]:
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            cur = conn.execute(
                """
                SELECT id, from_role, to_role, task, status, started_at,
                       completed_at, result, thread_id, user_id
                FROM agent.a2a_delegations
                WHERE id = %s::uuid
                """,
                (delegation_id,),
            )
            cols = [d[0] for d in cur.description] if cur.description else []
            row = cur.fetchone()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"a2a: {e}") from e

    if row is None:
        raise HTTPException(status_code=404, detail="Delegation not found")
    return _row_to_dict(row, cols)
