"""End-to-end integration tests for the scheduler (Phase-1 live gates).

Covers the flow documented in exec-scheduler.md §14 "Phase-1 gates —
live". Each test maps to one checkbox in the spec so verify-status
tracks exactly. Run with:

    RUN_INTEGRATION=1 pytest python-backend/tests/e2e/test_scheduler_flow.py -v

or:

    pytest -m integration -v

Prerequisites (conftest auto-skips otherwise):
* Postgres on :5433 with `hindsight_dev` DB
* NATS with JetStream on :4222
* go-appservice on :9000 (handler registers scheduler routes)
* python-backend alembic migrations up to 021 applied

Stack bringup:

    podman-compose --profile scheduler up -d

Teardown hooks in each test clean up DB rows they insert.
"""

from __future__ import annotations

import asyncio
import json
import time

import httpx
import pytest

from agent.scheduler import SUBJECT_JOB_EXECUTE
from agent.scheduler import db as scheduler_db

pytestmark = pytest.mark.integration


# ── Helpers ───────────────────────────────────────────────────────────────


async def _wait_for(
    predicate, *, timeout: float = 15.0, interval: float = 0.5
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if await predicate():
            return True
        await asyncio.sleep(interval)
    return False


# ── Phase-1 gate tests ────────────────────────────────────────────────────


async def test_gate_insert_task_via_tool(postgres_url):
    """Gate: insert a scheduled task via the python-backend DB layer
    (simulates the tool-call path without spinning up the full agent).
    """
    row = scheduler_db.InsertTaskRow(
        user_id="e2e-user-insert",
        source="chat_agent",
        kind="recurring",
        cron_expr="0 9 * * 1",
        scheduled_at_ms=None,
        tz="Europe/Zurich",
        prompt="e2e insert test",
        skill_ids=None,
        delivery_target={"kind": "matrix_room", "id": "!test:matrix.local"},
    )
    task_id = await scheduler_db.insert_task(row)
    try:
        got = await scheduler_db.get_task(task_id)
        assert got is not None
        assert got["status"] == "active"
        assert got["cron_expr"] == "0 9 * * 1"
        assert got["tz"] == "Europe/Zurich"
        assert got["source"] == "chat_agent"
    finally:
        # Hard delete — use the pool directly to avoid ownership filter.
        pool = await scheduler_db.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM scheduler.scheduled_tasks WHERE task_id = $1",
                task_id,
            )


async def test_gate_notify_trigger_fires(postgres_url):
    """Gate: after INSERT, pg_notify('scheduler_task_changed') payload
    reaches a LISTENer — this is what Go CronRegistry relies on for
    hot-reload.
    """
    import asyncpg

    conn = await asyncpg.connect(postgres_url)
    notifications: list[str] = []

    def on_notify(_conn, _pid, channel, payload):
        if channel == "scheduler_task_changed":
            notifications.append(payload)

    try:
        await conn.add_listener("scheduler_task_changed", on_notify)

        row = scheduler_db.InsertTaskRow(
            user_id="e2e-user-notify",
            source="api",
            kind="recurring",
            cron_expr="0 * * * *",
            scheduled_at_ms=None,
            tz="UTC",
            prompt="notify test",
            skill_ids=None,
            delivery_target=None,
        )
        task_id = await scheduler_db.insert_task(row)

        assert await _wait_for(
            lambda: asyncio.sleep(0) or bool(notifications),
            timeout=3.0,
            interval=0.1,
        ), "pg_notify did not arrive in 3s"

        assert any(
            json.loads(n).get("task_id") == task_id and json.loads(n).get("op") == "INSERT"
            for n in notifications
        )

        # Cleanup
        pool = await scheduler_db.get_pool()
        async with pool.acquire() as p_conn:
            await p_conn.execute(
                "DELETE FROM scheduler.scheduled_tasks WHERE task_id = $1",
                task_id,
            )
    finally:
        await conn.close()


async def test_gate_hard_cap_trigger_blocks(postgres_url):
    """Gate (§11.3 + migration 020): inserting the 51st active task for a
    user raises check_violation. Also validates that pause+insert+resume
    does NOT bypass (regression test for the sota-verify FAIL-2 fix).
    """
    import asyncpg

    user = "e2e-cap-user"
    pool = await scheduler_db.get_pool()
    inserted: list[str] = []

    async def _insert(idx: int) -> str:
        return await scheduler_db.insert_task(
            scheduler_db.InsertTaskRow(
                user_id=user,
                source="system",
                kind="recurring",
                cron_expr=f"{idx % 60} * * * *",
                scheduled_at_ms=None,
                tz="UTC",
                prompt=f"cap test {idx}",
                skill_ids=None,
                delivery_target=None,
            )
        )

    try:
        for i in range(50):
            inserted.append(await _insert(i))

        # 51st must fail with check_violation
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await _insert(50)

        # Bypass attempt: pause 30 → insert 30 more → resume should fail
        for tid in inserted[:30]:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE scheduler.scheduled_tasks "
                    "SET status='paused', updated_at=$1 WHERE task_id=$2",
                    int(time.time() * 1000),
                    tid,
                )
        for i in range(30):
            inserted.append(await _insert(100 + i))

        # Now try to resume the paused ones — cap should block
        async with pool.acquire() as conn:
            with pytest.raises(asyncpg.exceptions.CheckViolationError):
                await conn.execute(
                    "UPDATE scheduler.scheduled_tasks "
                    "SET status='active', updated_at=$1 "
                    "WHERE task_id=$2",
                    int(time.time() * 1000),
                    inserted[0],
                )
    finally:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM scheduler.scheduled_tasks WHERE user_id = $1",
                user,
            )


async def test_gate_ownership_enforced_on_rest(go_appservice_url):
    """Gate (sota-verify FAIL-3 fix): PATCH /tasks/{id} with a different
    user_id must return 404 (not 403, to avoid task-id enumeration) and
    must not mutate the row.
    """
    # Create a task owned by user A directly via DB
    task_id = await scheduler_db.insert_task(
        scheduler_db.InsertTaskRow(
            user_id="e2e-owner-a",
            source="api",
            kind="recurring",
            cron_expr="0 12 * * *",
            scheduled_at_ms=None,
            tz="UTC",
            prompt="ownership test",
            skill_ids=None,
            delivery_target=None,
        )
    )
    try:
        async with httpx.AsyncClient(base_url=go_appservice_url, timeout=5.0) as client:
            # User B tries to pause — expect 404
            r = await client.patch(
                f"/api/v1/scheduler/tasks/{task_id}",
                params={"user_id": "e2e-owner-b"},
                json={"status": "paused"},
            )
            assert r.status_code == 404, r.text

            # Confirm row still active
            got = await scheduler_db.get_task(task_id)
            assert got is not None and got["status"] == "active"

            # Correct owner — expect 200
            r = await client.patch(
                f"/api/v1/scheduler/tasks/{task_id}",
                params={"user_id": "e2e-owner-a"},
                json={"status": "paused"},
            )
            assert r.status_code == 200, r.text
    finally:
        pool = await scheduler_db.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM scheduler.scheduled_tasks WHERE task_id = $1",
                task_id,
            )


async def test_gate_run_now_publishes_to_jetstream(nats_url):
    """Gate: `schedule_run_now` publishes a JobExecutePayload to
    matrix.scheduler.job.execute. Subscriber consumes and ack's.
    """
    import nats as nats_lib

    # Create a task
    task_id = await scheduler_db.insert_task(
        scheduler_db.InsertTaskRow(
            user_id="e2e-runnow",
            source="api",
            kind="recurring",
            cron_expr="0 0 * * *",  # won't fire organically
            scheduled_at_ms=None,
            tz="UTC",
            prompt="run_now test",
            skill_ids=None,
            delivery_target=None,
        )
    )
    received: list[dict] = []
    nc = await nats_lib.connect(nats_url)
    try:
        js = nc.jetstream()
        # One-off ephemeral subscription to observe publishes — doesn't
        # compete with the durable scheduler-exec consumer.
        sub = await js.subscribe(SUBJECT_JOB_EXECUTE, stream="SCHEDULER")

        # Trigger publish via the publisher module (same path
        # schedule_run_now tool uses).
        from agent.scheduler.publisher import FireContext, publish_fire

        execution_id = await scheduler_db.begin_execution(task_id)
        await publish_fire(
            FireContext(
                task_id=task_id,
                execution_id=execution_id,
                owner_user_id="e2e-runnow",
                kind="recurring",
                prompt="run_now test",
                delivery_target=None,
                skill_ids=None,
                metadata=None,
            )
        )

        # Drain at least one message
        msg = await sub.next_msg(timeout=5.0)
        received.append(json.loads(msg.data))
        await msg.ack()

        assert received[-1]["task_id"] == task_id
        assert received[-1]["execution_id"] == execution_id
        assert received[-1]["owner_user_id"] == "e2e-runnow"
    finally:
        await nc.drain()
        pool = await scheduler_db.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM scheduler.scheduled_tasks WHERE task_id = $1",
                task_id,
            )
