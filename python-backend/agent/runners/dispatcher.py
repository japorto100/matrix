"""A/B dispatcher — routes turns between LangGraph runner and SimpleLoop (Phase-C P3).

This is the **single public entry point** that replaces the direct
``run_agent_loop`` call in :mod:`agent.app`. It does four things:

1. **Deterministic bucketing** — `hash(user_id) % 100` compared against
   `AGENT_SIMPLE_LOOP_PCT` (0-100). Same user → same variant across all
   their sessions. Per-user, not per-thread — matches the user's
   explicit request for stronger cross-session measurement validity.

2. **Kill-switch** — Valkey key ``agent:simple_loop:kill_switch`` (TTL-cached
   in-process for 5s so it doesn't block every request). Env-var
   ``AGENT_SIMPLE_LOOP_KILL_SWITCH`` is the fallback when Valkey is
   unavailable. Resolves Contrarian-MAJOR-2 (env-var-only = deploy-gated).

3. **Fire-and-forget A/B row INSERT** — client-generated UUID, non-blocking
   ``asyncio.create_task`` UPDATE after turn finishes. No RETURNING, no
   synchronous DB write on the hot path. Resolves Contrarian-CRITICAL-2.

4. **No silent fallback on SimpleLoop failure** — on exception mid-stream,
   we emit a clean error boundary (TextEnd + ErrorPacket marked
   ``runner=simple,fallback=true``) and then **stop**. Frontend sees one
   coherent error message instead of two overlapping text streams.
   Resolves Contrarian-BLOCKER-1. LangGraph errors propagate normally
   (runner.py emits its own ErrorPacket).

Quality-signal: we populate cost/tokens/error fields from the turn
itself. The user-satisfaction signal is filled in later by
``agent/harness/scorer.py`` joining on ``session_id`` and writing into
``harness_fitness_score`` — this dispatcher does not know about harness.
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import logging
import os
import time
import uuid
from collections.abc import AsyncGenerator

from agent.context import AgentExecutionContext
from agent.streaming import build_error_packet_with_failover, sse

logger = logging.getLogger(__name__)

__all__ = [
    "run_agent_loop_with_variant",
    "select_variant",
    "bucket_for_user",
    "is_kill_switch_active",
    "ab_status",
]


# ---------------------------------------------------------------------------
# Bucketing — deterministic, per-user sticky
# ---------------------------------------------------------------------------


def bucket_for_user(user_id: str) -> int:
    """Returns 0-99. Stable across processes. Same user → same bucket."""
    key = (user_id or "anonymous").encode()
    digest = hashlib.sha256(key).digest()
    return int.from_bytes(digest[:2], "big") % 100


# ---------------------------------------------------------------------------
# Kill-switch — Valkey-backed with in-process TTL cache
# ---------------------------------------------------------------------------

_KILL_SWITCH_CACHE_TTL_S = 5.0
_kill_switch_cached_until: float = 0.0
_kill_switch_cached_value: bool = False


async def is_kill_switch_active() -> bool:
    """Return True iff kill-switch is set. Valkey-first, env-var fallback.

    Cached 5 seconds in-process so a 100-req/s surge doesn't hammer Valkey.
    Resolves Contrarian-MAJOR-2: env-var-only kill-switch is deploy-gated,
    a Valkey key can be flipped live during an incident.
    """
    global _kill_switch_cached_until, _kill_switch_cached_value

    now = time.monotonic()
    if now < _kill_switch_cached_until:
        return _kill_switch_cached_value

    value = False
    try:
        import redis.asyncio as redis  # valkey speaks redis protocol

        url = os.environ.get("VALKEY_URL") or os.environ.get("PYTHON_REDIS_URL")
        if url:
            client = redis.from_url(url, decode_responses=True)
            raw = await client.get("agent:simple_loop:kill_switch")
            await client.aclose()
            if raw and str(raw).strip().lower() in ("1", "true", "yes", "on"):
                value = True
    except Exception:  # noqa: BLE001 — Valkey outage must not force an outage here
        logger.debug("kill-switch Valkey probe failed; falling through to env", exc_info=True)

    if not value:
        value = os.environ.get("AGENT_SIMPLE_LOOP_KILL_SWITCH", "").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    _kill_switch_cached_value = value
    _kill_switch_cached_until = now + _KILL_SWITCH_CACHE_TTL_S
    return value


# ---------------------------------------------------------------------------
# Variant selection
# ---------------------------------------------------------------------------


async def select_variant(user_id: str) -> tuple[str, int]:
    """Return (variant, bucket) for this user.

    Variant is ``"simple"`` or ``"langgraph"``. Bucket is the 0-99 audit
    trail column.
    """
    if await is_kill_switch_active():
        return "langgraph", bucket_for_user(user_id)

    try:
        pct = int(os.environ.get("AGENT_SIMPLE_LOOP_PCT", "0"))
    except ValueError:
        pct = 0
    pct = max(0, min(100, pct))

    bucket = bucket_for_user(user_id)
    if bucket < pct:
        return "simple", bucket
    return "langgraph", bucket


# ---------------------------------------------------------------------------
# A/B row creation — fire-and-forget with client UUID
# ---------------------------------------------------------------------------


async def _insert_ab_row(
    *,
    row_id: str,
    user_id: str,
    thread_id: str,
    variant: str,
    bucket: int,
) -> None:
    """INSERT the initial ab_experiments row. Runs as create_task — no await on hot path."""
    try:
        import psycopg

        dsn = os.environ.get(
            "HINDSIGHT_DB_URL",
            "postgresql://postgres@localhost:5433/hindsight_dev",
        )
        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            await conn.execute(
                """
                INSERT INTO agent.ab_experiments
                    (id, experiment_id, user_id, thread_id, variant, bucket_hash)
                VALUES (%s, 'phase-c-hybrid-loop', %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET experiment_id = EXCLUDED.experiment_id,
                    user_id       = EXCLUDED.user_id,
                    thread_id     = EXCLUDED.thread_id,
                    variant       = EXCLUDED.variant,
                    bucket_hash   = EXCLUDED.bucket_hash
                """,
                (row_id, user_id, thread_id, variant, bucket),
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("ab_experiments INSERT failed: %s", exc)


async def _mark_routing(
    row_id: str,
    *,
    routing_used: bool,
    routing_reason: str | None,
    routing_picked_model: str | None,
    user_id: str | None = None,
    thread_id: str | None = None,
) -> None:
    """ADR-001 G4 — fire-and-forget UPSERT of the routing dimension.

    Called from ``llm_node`` when smart-routing resolves a decision on
    iteration-0. Keeps the dispatcher hot-path free of extra await; the
    write piggy-backs on a new psycopg connection like `_mark_fallback`.
    """
    if not row_id:
        return
    try:
        import psycopg

        dsn = os.environ.get(
            "HINDSIGHT_DB_URL",
            "postgresql://postgres@localhost:5433/hindsight_dev",
        )
        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            await conn.execute(
                """
                INSERT INTO agent.ab_experiments
                    (
                        id,
                        experiment_id,
                        user_id,
                        thread_id,
                        variant,
                        bucket_hash,
                        routing_used,
                        routing_reason,
                        routing_picked_model
                    )
                VALUES
                    (
                        %s,
                        'phase-c-hybrid-loop',
                        COALESCE(%s, 'pending'),
                        %s,
                        'pending',
                        0,
                        %s,
                        %s,
                        %s
                    )
                ON CONFLICT (id) DO UPDATE
                SET routing_used = EXCLUDED.routing_used,
                    routing_reason = COALESCE(EXCLUDED.routing_reason, agent.ab_experiments.routing_reason),
                    routing_picked_model = COALESCE(EXCLUDED.routing_picked_model, agent.ab_experiments.routing_picked_model)
                """,
                (
                    row_id,
                    user_id,
                    thread_id,
                    routing_used,
                    routing_reason,
                    routing_picked_model,
                ),
            )
    except Exception:  # noqa: BLE001
        logger.debug(
            "ab_experiments routing UPDATE failed (row=%s)", row_id, exc_info=True
        )


async def _mark_fallback(row_id: str, error: str) -> None:
    try:
        import psycopg

        dsn = os.environ.get(
            "HINDSIGHT_DB_URL",
            "postgresql://postgres@localhost:5433/hindsight_dev",
        )
        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            await conn.execute(
                """
                UPDATE agent.ab_experiments
                SET fallback_triggered = true,
                    error = COALESCE(%s, error),
                    finished_at = now(),
                    finished_naturally = false
                WHERE id = %s
                """,
                (error[:500], row_id),
            )
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_agent_loop_with_variant(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Route this turn through the selected variant + record the outcome.

    Replaces the direct `run_agent_loop` import in `agent/app.py`. Same
    signature, same yielded SSE contract.
    """
    variant, bucket = await select_variant(ctx.user_id or "anonymous")
    row_id = str(uuid.uuid4())

    # Fire-and-forget row creation — dispatcher never waits for the DB
    # write to return before streaming SSE. Loss-on-crash is acceptable
    # for experiment data.
    asyncio.create_task(
        _insert_ab_row(
            row_id=row_id,
            user_id=ctx.user_id or "anonymous",
            thread_id=ctx.thread_id,
            variant=variant,
            bucket=bucket,
        )
    )

    # ADR-001 G4: thread the row id through the context so llm_node's
    # smart-routing block can mark the routing dimension on this run.
    # Frozen dataclass → use dataclasses.replace.
    ctx = dataclasses.replace(ctx, ab_row_id=row_id)

    if variant == "simple":
        async for chunk in _run_simple_with_guard(ctx, messages, row_id=row_id):
            yield chunk
    else:
        # LangGraph path — unchanged. Its own error-handling emits ErrorPacket.
        from agent.graph.runner import run_agent_loop

        async for chunk in run_agent_loop(ctx, messages):
            yield chunk


async def _run_simple_with_guard(
    ctx: AgentExecutionContext,
    messages: list[dict],
    *,
    row_id: str,
) -> AsyncGenerator[str, None]:
    """Wrap the SimpleLoop call so a mid-stream failure produces a clean error boundary.

    Resolves Contrarian-BLOCKER-1: silent fallback after partial stream
    emission produces two overlapping TextStartPackets with the same
    text_id, which AI SDK renders ambiguously. We do NOT fall back —
    instead we emit an ErrorPacket with failover metadata and stop.
    LangGraph has its own error path (runner.py:473).
    """
    from agent.runners.simple import run_simple_agent_loop

    try:
        async for chunk in run_simple_agent_loop(ctx, messages, ab_row_id=row_id):
            yield chunk
    except Exception as exc:
        logger.warning("SimpleLoop failed (row=%s): %s", row_id, exc)
        asyncio.create_task(
            _mark_fallback(row_id, f"{type(exc).__name__}: {exc}")
        )
        yield sse(build_error_packet_with_failover(exc, prefix="SimpleLoop error: "))


# ---------------------------------------------------------------------------
# Ops status endpoint helper
# ---------------------------------------------------------------------------


async def ab_status() -> dict:
    """Return the current A/B dispatcher state for `/api/v1/agent/ab/status`."""
    kill = await is_kill_switch_active()
    try:
        pct = int(os.environ.get("AGENT_SIMPLE_LOOP_PCT", "0"))
    except ValueError:
        pct = 0
    pct = max(0, min(100, pct))
    return {
        "active": pct > 0 and not kill,
        "percentage": pct,
        "kill_switch": kill,
        "variant_langgraph": "default",
        "variant_simple": "opt-in via AGENT_SIMPLE_LOOP_PCT",
    }
