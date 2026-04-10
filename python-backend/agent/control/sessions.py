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
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "sessions"])


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


def _table_exists(conn: psycopg.Connection, schema: str, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (schema, table),
    ).fetchone()
    return row is not None


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


@router.get("/sessions/{thread_id}")
async def get_session(thread_id: str) -> dict[str, Any]:
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            if not _table_exists(conn, "public", "checkpoints"):
                raise HTTPException(status_code=404, detail="checkpoints table not found")
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
            "metadata": json.loads(row[2]) if isinstance(row[2], str) else (row[2] or {}),
        }
        for row in rows
    ]
    return {"thread_id": thread_id, "checkpoints": checkpoints, "count": len(checkpoints)}


@router.delete("/sessions/{thread_id}")
async def kill_session(thread_id: str) -> dict[str, Any]:
    """Delete all checkpoints for a thread (Dev Mode only, approval-write)."""
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            if not _table_exists(conn, "public", "checkpoints"):
                return {"status": "no_table", "thread_id": thread_id, "deleted": 0}
            cur = conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,)
            )
            deleted = cur.rowcount or 0
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"kill session: {e}") from e

    return {"status": "killed", "thread_id": thread_id, "deleted": deleted}
