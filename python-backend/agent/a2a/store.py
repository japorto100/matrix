"""Persistent A2A delegation log.

The runtime audit stream remains the canonical trace for Meta-Harness. This
module mirrors accepted child delegations into ``agent.a2a_delegations`` so
Control/API consumers can query durable subagent history without replaying
every audit row.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

logger = logging.getLogger(__name__)


def _db_url() -> str:
    return os.environ.get("AUDIT_DB_URL") or os.environ.get("HINDSIGHT_DB_URL", "")


async def record_delegation_started(
    *,
    delegation_id: str,
    from_role: str,
    to_role: str,
    task: str,
    thread_id: str,
    user_id: str,
) -> bool:
    """Insert a running delegation row when a child request starts.

    Missing DB configuration is a normal local-dev state; persistence is best
    effort and must not block the agent turn.
    """
    db_url = _db_url()
    if not db_url:
        return False
    return await asyncio.to_thread(
        _record_started_sync,
        db_url,
        delegation_id,
        from_role,
        to_role,
        task,
        thread_id,
        user_id,
    )


async def record_delegation_finished(
    *,
    delegation_id: str,
    status: str,
    result: dict[str, Any],
) -> bool:
    """Mark a delegation terminal and persist a compact result payload."""
    db_url = _db_url()
    if not db_url:
        return False
    return await asyncio.to_thread(
        _record_finished_sync,
        db_url,
        delegation_id,
        status,
        result,
    )


def _record_started_sync(
    db_url: str,
    delegation_id: str,
    from_role: str,
    to_role: str,
    task: str,
    thread_id: str,
    user_id: str,
) -> bool:
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute(
                """
                INSERT INTO agent.a2a_delegations
                    (id, from_role, to_role, task, status, thread_id, user_id)
                VALUES
                    (%s::uuid, %s, %s, %s, 'running', %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    status = 'running',
                    task = EXCLUDED.task,
                    thread_id = EXCLUDED.thread_id,
                    user_id = EXCLUDED.user_id
                """,
                (
                    delegation_id,
                    from_role or "orchestrator",
                    to_role or "unknown",
                    task,
                    thread_id or None,
                    user_id or "local",
                ),
            )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("A2A delegation start persistence failed: %s", exc)
        return False


def _record_finished_sync(
    db_url: str,
    delegation_id: str,
    status: str,
    result: dict[str, Any],
) -> bool:
    terminal_status = str(status or "failed")
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute(
                """
                UPDATE agent.a2a_delegations
                SET status = %s,
                    completed_at = NOW(),
                    result = %s
                WHERE id = %s::uuid
                """,
                (terminal_status, Jsonb(result), delegation_id),
            )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("A2A delegation finish persistence failed: %s", exc)
        return False
