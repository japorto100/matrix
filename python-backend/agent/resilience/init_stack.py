"""Agent-resilience startup + health contract (exec-hermes Phase-B P1).

Seeds three process-wide singletons that the hot-path agent code reads
on every turn:

1. ``CredentialPool`` — via :func:`agent.resilience.credential_pool.get_credential_pool`
   (lazy; touched here just to surface any construction error early).
2. ``MemoryManager`` — via :func:`memory_fusion.memory_provider.auto_fusion_provider`.
   When Hindsight/MemPalace isn't reachable we retry a few times with
   exponential backoff, then fall back to ``None``. Callers handle ``None``
   by using the legacy hindsight-recall path.
3. ``ContextEngine`` — via :func:`context.context_engine.get_context_engine`
   (stateless ``DefaultContextEngine`` — just asserts construction).

Also probes the ``agent.sync_failures`` table (migration 022) so the
fire-and-forget ``_safe_sync_turn`` path in ``runner.py`` can skip the
INSERT branch if the table is missing (rolling deploy where pods start
before migrations complete).

Every init step fails **soft** — the service stays up even when all
three singletons fail, with every failure surfaced through:

* structured log warning (so dev sees it in console),
* ``agent.init.singleton_fail{name=X}`` span event (so OTel dashboards
  see it),
* ``_INIT_STATUS`` module-level state that ``/health/resilience`` reports
  (so load-balancers + ops dashboards can mark the pod unhealthy).

This keeps the operator-signal loud without making a single broken
subsystem block service startup.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

from agent.tracing import tracer as agent_tracer

logger = logging.getLogger(__name__)

__all__ = [
    "SubsystemStatus",
    "InitStatus",
    "init_status",
    "init_agent_resilience_stack",
    "resilience_health",
]


# ---------------------------------------------------------------------------
# Status bookkeeping
# ---------------------------------------------------------------------------


@dataclass
class SubsystemStatus:
    """Health of one resilience-stack subsystem."""

    name: str
    up: bool = False
    detail: str = ""


@dataclass
class InitStatus:
    """Process-wide health snapshot seeded by :func:`init_agent_resilience_stack`."""

    credential_pool: SubsystemStatus
    memory_manager: SubsystemStatus
    context_engine: SubsystemStatus
    sync_failures_table: SubsystemStatus

    def all_up(self) -> bool:
        return (
            self.credential_pool.up
            and self.memory_manager.up
            and self.context_engine.up
            and self.sync_failures_table.up
        )


_INIT_STATUS: InitStatus = InitStatus(
    credential_pool=SubsystemStatus(name="credential_pool", detail="not yet initialised"),
    memory_manager=SubsystemStatus(name="memory_manager", detail="not yet initialised"),
    context_engine=SubsystemStatus(name="context_engine", detail="not yet initialised"),
    sync_failures_table=SubsystemStatus(name="sync_failures_table", detail="not yet probed"),
)


def init_status() -> InitStatus:
    """Return the current resilience-stack init status (read-only view)."""
    return _INIT_STATUS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _emit_init_failure(name: str, error: str) -> None:
    """Emit the ``agent.init.singleton_fail`` span-event so OTel sees it.

    When OTel isn't enabled (``OTEL_ENABLED`` unset) ``agent_tracer`` is
    a NoopTracer so the span-body becomes a no-op — zero cost path.
    """
    try:
        with agent_tracer.start_as_current_span("agent.init.singleton_fail") as span:
            span.set_attribute("init.singleton.name", name)
            span.set_attribute("init.singleton.error", error[:500])
    except Exception:  # noqa: BLE001 — tracing failure must not break init
        logger.debug("failed to emit init.singleton_fail span", exc_info=True)


async def _probe_sync_failures_table() -> tuple[bool, str]:
    """``SELECT 1 FROM agent.sync_failures LIMIT 0`` — just checks existence.

    Rolling-deploy safety: if the new python-backend pod starts before
    migration 022 has run, the INSERT path in ``_safe_sync_turn`` would
    fail silently (because sync_turn itself is try/except-wrapped). By
    probing here we can skip the INSERT branch entirely when the table
    is missing — ops see the metric + health endpoint flip to degraded.
    """
    try:
        import asyncpg  # noqa: F401 (import-guard)

        dsn = (
            os.environ.get("SCHEDULER_DB_URL")
            or os.environ.get("HINDSIGHT_DB_URL")
            or os.environ.get("AUDIT_DB_URL")
        )
        if not dsn:
            return False, "no DB DSN env-var set (SCHEDULER_DB_URL / HINDSIGHT_DB_URL)"
        conn = await asyncpg.connect(dsn=dsn, timeout=2.0)
        try:
            await conn.execute("SELECT 1 FROM agent.sync_failures LIMIT 0")
        finally:
            await conn.close()
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"[:500]


async def _init_credential_pool() -> SubsystemStatus:
    try:
        from agent.resilience.credential_pool import get_credential_pool

        pool = get_credential_pool()
        return SubsystemStatus(
            name="credential_pool",
            up=True,
            detail=f"seeded as {pool.__class__.__name__}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("credential_pool init failed: %s", exc)
        _emit_init_failure("credential_pool", str(exc))
        return SubsystemStatus(
            name="credential_pool",
            up=False,
            detail=f"{type(exc).__name__}: {exc}"[:500],
        )


async def _init_memory_manager(
    *, max_retries: int = 3, backoff_base: float = 1.0
) -> SubsystemStatus:
    """Seed :class:`MemoryManager` singleton via ``auto_fusion_provider()``.

    Retries with exponential backoff (1s / 2s / 4s) because Hindsight
    and MemPalace might race with python-backend startup. After all
    retries fail we fall back to ``None`` — the runner's memory-recall
    path checks for ``None`` and falls through to the legacy hindsight
    engine directly (best-effort degradation, not a hard failure).
    """
    try:
        from memory_fusion.memory_provider import (
            MemoryManager,
            auto_fusion_provider,
            set_memory_manager,
        )
    except Exception as exc:  # noqa: BLE001
        _emit_init_failure("memory_manager", f"import: {exc}")
        return SubsystemStatus(
            name="memory_manager",
            up=False,
            detail=f"import failed: {exc}"[:500],
        )

    last_error = ""
    for attempt in range(max_retries):
        try:
            provider = await auto_fusion_provider()
            if provider is None:
                # auto_fusion_provider returned None legitimately (env-gated
                # to "disabled", or engine not available). Treat as
                # soft-off: ``_memory_manager`` stays None, callers fall
                # through to legacy path. Health flips to up=False so ops
                # know we're running without the new memory path.
                set_memory_manager(None)
                return SubsystemStatus(
                    name="memory_manager",
                    up=False,
                    detail="auto_fusion_provider returned None (no engine)",
                )
            manager = MemoryManager([provider])
            set_memory_manager(manager)
            return SubsystemStatus(
                name="memory_manager",
                up=True,
                detail=f"seeded with 1 provider ({provider.name})",
            )
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff_base * (2**attempt))

    logger.warning(
        "memory_manager init failed after %d attempts: %s", max_retries, last_error
    )
    _emit_init_failure("memory_manager", last_error)
    return SubsystemStatus(
        name="memory_manager",
        up=False,
        detail=last_error[:500],
    )


async def _init_context_engine() -> SubsystemStatus:
    try:
        from context.context_engine import get_context_engine

        engine = get_context_engine()
        return SubsystemStatus(
            name="context_engine",
            up=True,
            detail=f"seeded as {engine.__class__.__name__}",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("context_engine init failed: %s", exc)
        _emit_init_failure("context_engine", str(exc))
        return SubsystemStatus(
            name="context_engine",
            up=False,
            detail=f"{type(exc).__name__}: {exc}"[:500],
        )


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def init_agent_resilience_stack() -> InitStatus:
    """Seed the resilience-stack singletons. Safe to call exactly once per process.

    Registered as a FastAPI startup event handler by ``agent/app.py``.
    Idempotent: multiple calls just re-run the probes, which is fine
    because every step is side-effect-light (credential_pool and
    context_engine are lazy-init; memory_manager overwrites its
    singleton slot with the new manager).

    Returns the :class:`InitStatus` snapshot so callers can log a
    summary or fail their own startup if they need a hard-dependency
    on specific subsystems.
    """
    global _INIT_STATUS

    credential = await _init_credential_pool()
    memory = await _init_memory_manager()
    context = await _init_context_engine()

    sync_table_up, sync_detail = await _probe_sync_failures_table()
    sync_status = SubsystemStatus(
        name="sync_failures_table",
        up=sync_table_up,
        detail=sync_detail if not sync_table_up else "SELECT-probe succeeded",
    )
    if not sync_table_up:
        _emit_init_failure("sync_failures_table", sync_detail)

    _INIT_STATUS = InitStatus(
        credential_pool=credential,
        memory_manager=memory,
        context_engine=context,
        sync_failures_table=sync_status,
    )

    logger.info(
        "resilience stack init: credential_pool=%s memory_manager=%s "
        "context_engine=%s sync_failures_table=%s",
        credential.up,
        memory.up,
        context.up,
        sync_table_up,
    )
    return _INIT_STATUS


def resilience_health() -> dict[str, Any]:
    """JSON-serialisable body for the ``GET /health/resilience`` endpoint.

    Shape::

        {
          "status": "up" | "degraded",
          "credential_pool": {"up": bool, "detail": "..."},
          "memory_manager":  {"up": bool, "detail": "..."},
          "context_engine":  {"up": bool, "detail": "..."},
          "sync_failures_table": {"up": bool, "detail": "..."}
        }

    Callers (``agent/app.py``) return HTTP 200 if ``status == "up"``,
    HTTP 503 otherwise so load-balancers can mark the pod unhealthy.
    """
    return {
        "status": "up" if _INIT_STATUS.all_up() else "degraded",
        "credential_pool": {
            "up": _INIT_STATUS.credential_pool.up,
            "detail": _INIT_STATUS.credential_pool.detail,
        },
        "memory_manager": {
            "up": _INIT_STATUS.memory_manager.up,
            "detail": _INIT_STATUS.memory_manager.detail,
        },
        "context_engine": {
            "up": _INIT_STATUS.context_engine.up,
            "detail": _INIT_STATUS.context_engine.detail,
        },
        "sync_failures_table": {
            "up": _INIT_STATUS.sync_failures_table.up,
            "detail": _INIT_STATUS.sync_failures_table.detail,
        },
    }
