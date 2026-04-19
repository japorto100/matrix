"""asyncpg helpers for scheduler.scheduled_tasks + task_executions.

Go-side owns writes to scheduled_tasks.{last_run_at,execution_count} and
reads everything. Python owns:

* INSERT into scheduled_tasks at tool-confirmation time.
* UPDATE task_executions when an agent-turn finishes (running→completed/failed).
* Any per-user listing / mutation triggered via agent-tool invocations.

This module uses a standalone asyncpg pool (separate from the main Hindsight
pool) to keep scheduler credentials opt-in. The DSN comes from
``SCHEDULER_DB_URL`` or falls back to ``HINDSIGHT_DB_URL``.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

try:
    import asyncpg
except ImportError:  # pragma: no cover — asyncpg is a runtime requirement
    asyncpg = None  # type: ignore[assignment]


_POOL: Any | None = None
_POOL_LOCK = asyncio.Lock()


def _dsn() -> str:
    dsn = os.environ.get("SCHEDULER_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
    if not dsn:
        raise RuntimeError(
            "scheduler.db: neither SCHEDULER_DB_URL nor HINDSIGHT_DB_URL set"
        )
    return dsn


async def get_pool() -> Any:
    """Return a lazily-initialised asyncpg pool."""
    if asyncpg is None:  # pragma: no cover
        raise RuntimeError("asyncpg not installed")
    global _POOL
    if _POOL is not None:
        return _POOL
    async with _POOL_LOCK:
        if _POOL is not None:
            return _POOL
        _POOL = await asyncpg.create_pool(
            dsn=_dsn(),
            min_size=1,
            max_size=4,
            command_timeout=10,
        )
    return _POOL


async def close_pool() -> None:
    global _POOL
    if _POOL is not None:
        pool = _POOL
        _POOL = None
        await pool.close()


def now_ms() -> int:
    return int(time.time() * 1000)


def new_task_id() -> str:
    return secrets.token_hex(16)


@dataclass
class InsertTaskRow:
    """Input shape for inserting a scheduled_tasks row from an agent-tool."""

    user_id: str
    source: str  # chat_agent | chat_matrix_dm | chat_matrix_group | ...
    kind: str  # recurring | one_shot | reminder | routine | condition | infra
    cron_expr: str | None
    scheduled_at_ms: int | None
    tz: str
    prompt: str | None
    skill_ids: list[str] | None
    delivery_target: dict | None
    max_executions: int | None = None
    metadata: dict | None = None


async def count_active_for_user(user_id: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT COUNT(*) FROM scheduler.scheduled_tasks
            WHERE user_id = $1 AND status = 'active'
            """,
            user_id,
        )


async def count_recent_inserts_for_user(
    user_id: str, within_ms: int = 60_000
) -> int:
    """Count rows the user created in the last ``within_ms`` milliseconds.

    Powers the per-turn rate-limit in ``schedule_task``: a prompt-
    injected "add 20 tasks" turn spends one INSERT per tool-call, so
    bucketing on created_at over the last minute catches the flood
    without needing per-turn thread-local state (which wouldn't survive
    a worker restart mid-turn anyway).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT COUNT(*) FROM scheduler.scheduled_tasks
            WHERE user_id = $1
              AND created_at >= $2
            """,
            user_id,
            now_ms() - max(int(within_ms), 1_000),
        )


async def insert_task(row: InsertTaskRow) -> str:
    """Insert a new scheduled task. Returns the generated task_id.

    Raises asyncpg.CheckViolationError when hard-cap trigger fires (50 active
    per user). Caller (agent-tool) is responsible for surfacing a friendly
    error message to the user.
    """
    pool = await get_pool()
    task_id = new_task_id()
    nowms = now_ms()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO scheduler.scheduled_tasks (
                task_id, user_id, source, kind, cron_expr, scheduled_at,
                tz, prompt, skill_ids, delivery_target, status,
                max_executions, execution_count, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                      'active', $11, 0, $12, $12)
            """,
            task_id,
            row.user_id,
            row.source,
            row.kind,
            row.cron_expr,
            row.scheduled_at_ms,
            row.tz,
            row.prompt,
            row.skill_ids,
            json.dumps(row.delivery_target) if row.delivery_target else None,
            row.max_executions,
            nowms,
        )
    return task_id


async def get_task(task_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM scheduler.scheduled_tasks WHERE task_id = $1
            """,
            task_id,
        )
    return dict(row) if row else None


async def list_tasks_for_user(user_id: str, limit: int = 50) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT task_id, user_id, source, kind, cron_expr, scheduled_at,
                   tz, prompt, delivery_target, status, execution_count,
                   last_run_at, created_at
            FROM scheduler.scheduled_tasks
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
    return [dict(r) for r in rows]


async def patch_task_fields(
    task_id: str,
    user_id: str,
    *,
    prompt: str | None = None,
    cron_expr: str | None = None,
    scheduled_at_ms: int | None = None,
    tz: str | None = None,
    delivery_target: dict | None = None,
    max_executions: int | None = None,
) -> bool:
    """Patch editable fields on a scheduled task (owner-gated).

    Non-editable: user_id, source, kind (kind change would invalidate the
    trigger-CHECK constraint). ``None`` = leave unchanged; any other value
    overwrites. Returns True if a row was updated.
    """
    assignments: list[str] = []
    args: list = []
    idx = 1

    def add(col: str, value) -> None:
        nonlocal idx
        assignments.append(f"{col} = ${idx}")
        args.append(value)
        idx += 1

    if prompt is not None:
        add("prompt", prompt)
    if cron_expr is not None:
        add("cron_expr", cron_expr)
    if scheduled_at_ms is not None:
        add("scheduled_at", scheduled_at_ms)
    if tz is not None:
        add("tz", tz)
    if delivery_target is not None:
        add("delivery_target", json.dumps(delivery_target))
    if max_executions is not None:
        add("max_executions", max_executions)
    if not assignments:
        return False  # nothing to update

    # Always bump updated_at so LISTEN/NOTIFY hot-reload triggers.
    add("updated_at", now_ms())

    sql = f"""
        UPDATE scheduler.scheduled_tasks
        SET {", ".join(assignments)}
        WHERE task_id = ${idx} AND user_id = ${idx + 1}
    """
    args.append(task_id)
    args.append(user_id)

    pool = await get_pool()
    async with pool.acquire() as conn:
        tag = await conn.execute(sql, *args)
    return tag.endswith("1")


async def patch_status(task_id: str, user_id: str, new_status: str) -> bool:
    """Update status (paused/active/cancelled). Enforces user-ownership.

    Returns True when a row was updated, False when no row matched
    (wrong user_id or missing task_id).
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        tag = await conn.execute(
            """
            UPDATE scheduler.scheduled_tasks
            SET status = $1, updated_at = $2
            WHERE task_id = $3 AND user_id = $4
            """,
            new_status,
            now_ms(),
            task_id,
            user_id,
        )
    return tag.endswith("1")


async def begin_execution(task_id: str) -> str:
    """Insert a task_executions row in status='running' and return the id.

    Used by ``schedule_run_now`` — the Python-driven manual fire path.
    Normal cron-driven fires use the Go-side equivalent in PgStore.
    """
    pool = await get_pool()
    execution_id = new_task_id()
    started_ms = now_ms()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO scheduler.task_executions
                (execution_id, task_id, started_at, status)
            VALUES ($1, $2, $3, 'running')
            """,
            execution_id,
            task_id,
            started_ms,
        )
        await conn.execute(
            """
            UPDATE scheduler.scheduled_tasks
            SET last_run_at = $1,
                execution_count = execution_count + 1,
                updated_at = $1
            WHERE task_id = $2
            """,
            started_ms,
            task_id,
        )
    return execution_id


async def finish_execution(
    execution_id: str,
    status: str,
    *,
    result_summary: str | None = None,
    error: str | None = None,
    trace_id: str | None = None,
    output_ref: str | None = None,
) -> None:
    """Update a task_executions row to terminal state with summary/error."""
    pool = await get_pool()
    completed_ms = now_ms()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE scheduler.task_executions
            SET status = $1,
                completed_at = $2,
                result_summary = $3,
                error = $4,
                trace_id = COALESCE($5, trace_id),
                output_ref = COALESCE($6, output_ref),
                duration_ms = GREATEST(
                    COALESCE($2 - started_at, 0), 0
                )::int
            WHERE execution_id = $7
            """,
            status,
            completed_ms,
            result_summary,
            error,
            trace_id,
            output_ref,
            execution_id,
        )


async def list_executions(task_id: str, limit: int = 20) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT execution_id, task_id, started_at, completed_at, status,
                   result_summary, error, trace_id, duration_ms
            FROM scheduler.task_executions
            WHERE task_id = $1
            ORDER BY started_at DESC
            LIMIT $2
            """,
            task_id,
            limit,
        )
    return [dict(r) for r in rows]
