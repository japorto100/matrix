"""Infrastructure handlers for service-user scheduled tasks.

When the Go scheduler fires a task whose owner_user_id matches
``service_user_id()``, the Python subscriber routes it here instead of
spinning up an agent turn. Phase-1 covers ``infra.memory_prune`` and
``infra.health_ping``; more handlers land as the 15-use-case taxonomy
from exec-scheduler.md §3 gets implemented.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


async def handle_system_task(payload: dict) -> None:
    task_id = payload.get("task_id", "")
    kind = payload.get("kind", "")
    log.info("scheduler.handlers: system task task_id=%s kind=%s", task_id, kind)

    # Dispatch by task_id — the Go side publishes with task_id that
    # encodes the handler type (e.g. ``infra.memory_prune``). For Phase-1
    # the infra handlers are triggered from Go in-process PeriodicJobs,
    # not via NATS, so anything reaching here is a no-op unless the
    # task_id begins with a known prefix.
    if task_id.startswith("infra.memory_prune"):
        await _memory_prune()
    elif task_id.startswith("infra.health_ping"):
        log.debug("scheduler.handlers: health_ping tick")
    else:
        log.debug("scheduler.handlers: no handler for system task %s", task_id)


async def _memory_prune() -> None:
    """Delete memory sessions older than 30 days. Phase-1 stub — wire the
    full prune logic when exec-memory §retention lands.
    """
    log.info("scheduler.handlers: memory_prune invoked (stub)")
