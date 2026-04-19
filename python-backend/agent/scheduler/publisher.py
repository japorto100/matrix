"""Publish JobExecutePayload to JetStream from Python (schedule_run_now).

Normal fires originate from Go's River — this module gives agent-tools a
symmetric path for manual triggering. The JSON shape must match
``go-appservice/internal/scheduler/payloads.go JobExecutePayload``.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass

from agent.scheduler import SUBJECT_JOB_EXECUTE, jetstream_stream

try:
    import nats
    from nats.js.errors import NotFoundError
except ImportError:  # pragma: no cover
    nats = None  # type: ignore[assignment]

log = logging.getLogger(__name__)


@dataclass
class FireContext:
    task_id: str
    execution_id: str
    owner_user_id: str
    kind: str
    prompt: str | None
    delivery_target: dict | None
    skill_ids: list[str] | None
    metadata: dict | None
    trace_id: str | None = None


def _nats_url() -> str:
    return os.environ.get("NATS_URL", "nats://localhost:4222")


async def publish_fire(fire: FireContext) -> None:
    """Publish a JobExecutePayload to the SCHEDULER JetStream.

    Idempotent on the subscriber side: the subscriber dedups via
    (task_id, execution_id) — two publishes with the same execution_id
    collide on the UNIQUE PK of task_executions, so the second ack-loops
    harmlessly.
    """
    if nats is None:
        raise RuntimeError("nats-py not installed — can't publish manual fire")

    payload = {
        "task_id": fire.task_id,
        "execution_id": fire.execution_id,
        "owner_user_id": fire.owner_user_id,
        "kind": fire.kind,
        "prompt": fire.prompt or "",
        "skill_ids": fire.skill_ids or [],
        "delivery_target": fire.delivery_target,
        "metadata": fire.metadata,
        "trace_id": fire.trace_id or "",
        "fired_at_ms": int(time.time() * 1000),
    }
    body = json.dumps(payload).encode("utf-8")

    nc = await nats.connect(_nats_url(), name="scheduler-publisher")
    try:
        js = nc.jetstream()
        # Publish with stream binding — fails fast if the stream is
        # absent (prevents silent blackhole when Go hasn't booted).
        try:
            await js.publish(
                SUBJECT_JOB_EXECUTE,
                body,
                stream=jetstream_stream(),
            )
        except NotFoundError as exc:
            raise RuntimeError(
                f"JetStream stream {jetstream_stream()!r} not found — "
                "scheduler Go-service probably not running"
            ) from exc
    finally:
        await nc.drain()
    log.info(
        "scheduler.publisher: manual fire published task_id=%s exec_id=%s",
        fire.task_id,
        fire.execution_id,
    )
