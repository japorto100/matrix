"""FastAPI lifespan helpers for the scheduler subscriber.

Call ``start_scheduler_subscriber()`` from the app startup block and
``stop_scheduler_subscriber()`` from shutdown. Opt-in via
``SCHEDULER_SUBSCRIBER_ENABLED=true`` so legacy deployments (no NATS
JetStream, or not yet migrated) don't fail startup.
"""

from __future__ import annotations

import logging
import os

from agent.scheduler.subscriber import Subscriber

log = logging.getLogger(__name__)

_subscriber: Subscriber | None = None


def _enabled() -> bool:
    v = os.environ.get("SCHEDULER_SUBSCRIBER_ENABLED", "").strip().lower()
    return v in {"1", "true", "yes", "on"}


async def start_scheduler_subscriber() -> None:
    global _subscriber
    if not _enabled():
        log.info(
            "scheduler.subscriber disabled (set SCHEDULER_SUBSCRIBER_ENABLED=true to enable)"
        )
        return
    if _subscriber is not None:
        return
    _subscriber = Subscriber()
    try:
        await _subscriber.start()
    except Exception:
        log.exception("scheduler.subscriber: start failed")
        _subscriber = None


async def stop_scheduler_subscriber() -> None:
    global _subscriber
    if _subscriber is None:
        return
    try:
        await _subscriber.stop()
    except Exception:
        log.exception("scheduler.subscriber: stop failed")
    _subscriber = None
