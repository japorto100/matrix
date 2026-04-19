"""NATS JetStream durable-consumer for matrix.scheduler.job.execute.

Lifecycle:
  1. Connect to NATS, get JetStream context.
  2. Ensure SCHEDULER stream exists (Go-side normally creates it; we're
     defensive in case the subscriber starts first).
  3. Pull-subscribe with durable consumer name=queue_group() so two
     subscribers deliver each message once across the pool.
  4. On message: deserialize payload, run agent turn (or infra handler
     for service-user tasks), finish_execution, ack.

Cancellation: ``Subscriber.stop()`` cancels the consume loop and drains
outstanding acks. Call from app.py lifespan shutdown.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from agent.scheduler import (
    SUBJECT_JOB_EXECUTE,
    is_service_user,
    jetstream_stream,
    queue_group,
)
from agent.scheduler import db as scheduler_db
from agent.scheduler import handlers as scheduler_handlers
from agent.scheduler.runner_adapter import execute_for_scheduler, summary_line

try:
    import nats
    from nats.js.api import (
        ConsumerConfig,
        DeliverPolicy,
        RetentionPolicy,
        StorageType,
        StreamConfig,
    )
    from nats.js.errors import NotFoundError
except ImportError:  # pragma: no cover
    nats = None  # type: ignore[assignment]


log = logging.getLogger(__name__)


class Subscriber:
    """Background task that consumes scheduler job-fire messages."""

    def __init__(
        self,
        nats_url: str | None = None,
        *,
        turn_runner=execute_for_scheduler,
    ) -> None:
        self._nats_url = nats_url or os.environ.get(
            "NATS_URL", "nats://localhost:4222"
        )
        self._turn_runner = turn_runner
        self._nc = None
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if nats is None:
            log.warning("scheduler.subscriber: nats-py not installed — skipping")
            return
        self._nc = await nats.connect(self._nats_url, name="scheduler-subscriber")
        js = self._nc.jetstream()
        await _ensure_stream(js, jetstream_stream())
        await _ensure_consumer(js, jetstream_stream(), queue_group())

        self._task = asyncio.create_task(self._run(js), name="scheduler-subscriber")
        log.info(
            "scheduler.subscriber: started stream=%s durable=%s",
            jetstream_stream(),
            queue_group(),
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except TimeoutError:
                self._task.cancel()
        if self._nc is not None:
            await self._nc.drain()
        await scheduler_db.close_pool()
        log.info("scheduler.subscriber: stopped")

    async def _run(self, js) -> None:
        sub = await js.pull_subscribe(
            SUBJECT_JOB_EXECUTE,
            durable=queue_group(),
            stream=jetstream_stream(),
        )
        while not self._stop_event.is_set():
            try:
                msgs = await sub.fetch(batch=1, timeout=2.0)
            except TimeoutError:
                continue
            except Exception as exc:  # noqa: BLE001
                log.warning("scheduler.subscriber: fetch error %s", exc)
                await asyncio.sleep(1.0)
                continue
            for msg in msgs:
                await self._dispatch(msg)

    async def _dispatch(self, msg) -> None:
        try:
            payload = json.loads(msg.data)
        except json.JSONDecodeError as exc:
            log.error(
                "scheduler.subscriber: invalid payload %r: %s",
                msg.data[:200],
                exc,
            )
            # Ack so we don't loop on poisoned payloads. Future: dead-letter.
            await msg.ack()
            return

        execution_id = payload.get("execution_id") or ""
        owner = payload.get("owner_user_id") or ""
        kind = payload.get("kind") or "recurring"

        # Heartbeat: extend JetStream's ack_wait window every 30s while we
        # work. Protects against redelivery-during-execution when an agent
        # turn runs long (multi-step tool use, slow LLM provider).
        heartbeat = asyncio.create_task(_heartbeat_loop(msg))
        try:
            if is_service_user(owner):
                await scheduler_handlers.handle_system_task(payload)
                await scheduler_db.finish_execution(
                    execution_id, "completed", result_summary="system task ok"
                )
            else:
                await _run_user_task(payload, self._turn_runner)
            await msg.ack()
        except Exception as exc:  # noqa: BLE001
            log.exception(
                "scheduler.subscriber: dispatch failed task_id=%s kind=%s",
                payload.get("task_id"),
                kind,
            )
            try:
                await scheduler_db.finish_execution(
                    execution_id,
                    "failed",
                    error=f"{type(exc).__name__}: {exc}"[:500],
                )
            except Exception:
                log.exception("scheduler.subscriber: finish_execution failed")
            # Negative-ack so River/JetStream retry policy kicks in.
            await msg.nak(delay=30)
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass


async def _heartbeat_loop(msg, interval: float = 30.0) -> None:
    """Call msg.in_progress() every ``interval`` seconds until cancelled.

    Extends the consumer's ack_wait deadline so a long-running agent turn
    isn't redelivered to another subscriber while still executing.
    """
    while True:
        await asyncio.sleep(interval)
        try:
            await msg.in_progress()
        except Exception:  # noqa: BLE001 — best-effort, don't kill dispatch
            log.debug(
                "scheduler.subscriber: in_progress heartbeat failed (non-fatal)"
            )
            return


async def _run_user_task(payload: dict, runner) -> None:
    """Build the AgentExecutionContext for the owning user and run the turn."""
    from agent.context import AgentExecutionContext
    from agent.tools.registry import ToolRegistry

    task_id = payload.get("task_id", "")
    execution_id = payload.get("execution_id", "")
    owner = payload.get("owner_user_id", "")
    prompt = payload.get("prompt") or ""

    # Minimal context — full credentials / api-key wiring is Phase-1b.
    # For now we run with system_prompt=prompt and let the loop extract
    # tools from the default registry.
    registry = ToolRegistry.load(None)
    ctx = AgentExecutionContext(
        user_id=owner,
        thread_id=f"scheduler:{task_id}:{execution_id}",
        model=os.environ.get("SCHEDULER_DEFAULT_MODEL", "claude-sonnet"),
        system_prompt="You are running a scheduled task on behalf of the user.",
        tools=tuple(registry.all()),
        api_key=os.environ.get("SCHEDULER_SERVICE_API_KEY"),
    )
    result = await runner(ctx, [{"role": "user", "content": prompt}])
    status = "failed" if result.error else "completed"
    await scheduler_db.finish_execution(
        execution_id,
        status,
        result_summary=summary_line(result),
        error=result.error,
        trace_id=result.trace_id,
    )


async def _ensure_stream(js, name: str) -> None:
    if nats is None:
        return
    try:
        await js.stream_info(name)
        return
    except NotFoundError:
        pass
    await js.add_stream(
        StreamConfig(
            name=name,
            subjects=["matrix.scheduler.>"],
            retention=RetentionPolicy.LIMITS,
            storage=StorageType.FILE,
        )
    )
    log.info("scheduler.subscriber: created stream %s", name)


async def _ensure_consumer(js, stream: str, durable: str) -> None:
    if nats is None:
        return
    try:
        await js.consumer_info(stream, durable)
        return
    except NotFoundError:
        pass
    await js.add_consumer(
        stream,
        ConsumerConfig(
            durable_name=durable,
            deliver_policy=DeliverPolicy.ALL,
            # ack_wait headroom for long agent turns. Subscriber also
            # calls msg.in_progress() every 30s for turns > 60s so this
            # limit rarely matters in practice, but we pad it anyway.
            ack_wait=600,
            max_deliver=5,
        ),
    )
    log.info(
        "scheduler.subscriber: created durable consumer stream=%s durable=%s",
        stream,
        durable,
    )
