"""Scheduler subscriber + agent-tools for exec-scheduler Phase-1.

This package consumes NATS JetStream messages published by the Go-side
scheduler (``go-appservice/internal/scheduler``) and routes them to agent
turns or internal handlers.

Lane-F constants live here so Lane C (subscriber + tools) has a single
import surface. Keep in sync with ``go-appservice/internal/scheduler/scheduler.go``
(constants duplicated intentionally — cross-language parity check via
Lane-E tests).
"""

from __future__ import annotations

import os

DEFAULT_SERVICE_USER_ID = "scheduler-service"
DEFAULT_JETSTREAM_STREAM = "SCHEDULER"
DEFAULT_QUEUE_GROUP = "scheduler-exec"

SCHEMA = "scheduler"

SUBJECT_JOB_EXECUTE = "matrix.scheduler.job.execute"
SUBJECT_HEARTBEAT = "matrix.scheduler.heartbeat"


def service_user_id() -> str:
    """Return the configured infra-task user id.

    Infra-tasks (health-ping, memory-prune, metric-rollup) persist rows
    in ``scheduler.scheduled_tasks`` with ``user_id=service_user_id()``.
    The Python subscriber recognises this id and skips credential-lookup —
    infra-tasks don't call LLMs in Phase 1.
    """
    return os.environ.get("SCHEDULER_SERVICE_USER_ID") or DEFAULT_SERVICE_USER_ID


def is_service_user(user_id: str | None) -> bool:
    """True when ``user_id`` is the scheduler service account."""
    return bool(user_id) and user_id == service_user_id()


def jetstream_stream() -> str:
    return (
        os.environ.get("SCHEDULER_JETSTREAM_STREAM") or DEFAULT_JETSTREAM_STREAM
    )


def queue_group() -> str:
    return os.environ.get("SCHEDULER_QUEUE_GROUP") or DEFAULT_QUEUE_GROUP


__all__ = [
    "DEFAULT_SERVICE_USER_ID",
    "DEFAULT_JETSTREAM_STREAM",
    "DEFAULT_QUEUE_GROUP",
    "SCHEMA",
    "SUBJECT_JOB_EXECUTE",
    "SUBJECT_HEARTBEAT",
    "service_user_id",
    "is_service_user",
    "jetstream_stream",
    "queue_group",
]
