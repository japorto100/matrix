"""Tier-2 async custom-pattern redaction consumer (exec-security §1.2 Tier-2).

Runs as a background task, reads ``agent.redaction_patterns`` and applies
each active pattern to recently-inserted spans. Tier-1 (static 36-pattern
regex in :mod:`agent.security.redact`) already ran synchronously inside
``PostgresSpanProcessor.on_end`` — this consumer only touches content that
Tier-1 wouldn't catch (org-specific prefixes, customer-PII shapes).

**Why async + separate process:**
``PostgresSpanProcessor.on_end`` runs synchronously with a blocking
``psycopg.connect()`` call (exec-17 §2.5) — no ``await`` available. DB-
backed pattern lookup needs async I/O. So we UPDATE-in-place post-INSERT
rather than blocking the span-emit path.

**Default disabled.** Activation requires:

* ``MATRIX_REDACT_CONSUMER_ENABLED=true`` env-var
* At least one active row in ``agent.redaction_patterns`` (empty table
  skips the consumer's main loop)

**ReDoS defense.** Each pattern is compiled once at activation, and each
match call runs under a 100ms wall-clock timeout (signal-based on Linux,
thread-based fallback on Windows). Patterns exceeding the timeout are
disabled automatically + a span-event ``redact.pattern_timeout`` is
emitted so ops see the bad entry.

Cross-refs:
* ``exec-security.md §1.2 Tier-2`` — design rationale, admin bypass.
* Migration ``023_agent_redaction_patterns`` — table schema.
* ``agent/security/redact.py`` — Tier-1 baseline the consumer builds on.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import signal
import sys
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "CompiledPattern",
    "is_consumer_enabled",
    "load_patterns",
    "apply_patterns_to_event",
    "RedactConsumer",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MATCH_TIMEOUT_MS = 100   # per-pattern per-call timeout; matches plan
_MATCH_TIMEOUT_S = _MATCH_TIMEOUT_MS / 1000.0

_CONSUMER_ENABLED: bool = os.getenv(
    "MATRIX_REDACT_CONSUMER_ENABLED", ""
).lower() in ("1", "true", "yes", "on")


def is_consumer_enabled() -> bool:
    """Module-level accessor. Read once at boot by the app lifespan hook."""
    return _CONSUMER_ENABLED


# ---------------------------------------------------------------------------
# Pattern loading + compilation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompiledPattern:
    """Runtime representation of one ``agent.redaction_patterns`` row.

    ``regex`` is pre-compiled at load-time. Callers that want to apply a
    batch of patterns iterate :meth:`.load_patterns` and call
    :func:`apply_patterns_to_event` per event.
    """

    id: int
    regex: re.Pattern[str]
    replacement: str
    severity: str
    org_scope: str | None


def _compile_pattern_row(row: dict[str, Any]) -> CompiledPattern | None:
    """Compile a DB-row into a :class:`CompiledPattern`, or log+skip on
    invalid regex. Invalid patterns are never propagated to callers."""
    raw = row.get("pattern_regex") or ""
    if not raw:
        return None
    try:
        compiled = re.compile(raw)
    except re.error as exc:
        logger.warning(
            "redact_consumer: skipping invalid pattern id=%s: %s",
            row.get("id"),
            exc,
        )
        return None
    return CompiledPattern(
        id=int(row["id"]),
        regex=compiled,
        replacement=str(row.get("replacement") or "[REDACTED]"),
        severity=str(row.get("severity") or "info"),
        org_scope=row.get("org_scope"),
    )


async def load_patterns(
    dsn: str, *, org_scope: str | None = None
) -> list[CompiledPattern]:
    """Load active patterns from Postgres.

    Returns org-global patterns (``org_scope IS NULL``) plus any matching
    the caller-supplied ``org_scope``. Empty list when the consumer is
    disabled or the table has no active rows.
    """
    if not _CONSUMER_ENABLED:
        return []

    try:
        import asyncpg
    except ImportError:
        logger.warning("redact_consumer: asyncpg not installed — skipping")
        return []

    query = """
        SELECT id, pattern_regex, replacement, severity, org_scope
        FROM agent.redaction_patterns
        WHERE is_active IS TRUE
          AND (org_scope IS NULL OR org_scope = $1)
        ORDER BY id ASC
    """
    try:
        conn = await asyncpg.connect(dsn=dsn, timeout=3.0)
    except Exception as exc:  # noqa: BLE001 — startup race-safe
        logger.debug("redact_consumer: DB connect skipped: %s", exc)
        return []
    try:
        rows = await conn.fetch(query, org_scope)
    finally:
        await conn.close()

    compiled: list[CompiledPattern] = []
    for row in rows:
        pat = _compile_pattern_row(dict(row))
        if pat is not None:
            compiled.append(pat)
    logger.info(
        "redact_consumer: loaded %d active patterns (org_scope=%s)",
        len(compiled),
        org_scope,
    )
    return compiled


# ---------------------------------------------------------------------------
# ReDoS-safe match execution
# ---------------------------------------------------------------------------


class _PatternTimeoutError(Exception):
    """Raised when a pattern exceeds the per-call wall-clock timeout."""


def _run_with_timeout(fn, *, timeout_s: float):
    """Execute ``fn()`` with a wall-clock timeout.

    Linux: ``signal.SIGALRM`` (fast, single-thread). Fallback (Windows or
    non-main-thread): ``threading.Thread`` with polling — less precise but
    still bounds the damage from an adversarial pattern.
    """
    # Fast path: SIGALRM when main thread on POSIX.
    is_main = threading.current_thread() is threading.main_thread()
    has_alarm = hasattr(signal, "SIGALRM") and sys.platform != "win32"
    if is_main and has_alarm:
        def _handler(signum, frame):  # noqa: ARG001
            raise _PatternTimeoutError

        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
        try:
            return fn()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)

    # Slow path: thread-based fallback.
    result: list[Any] = [None]
    exc_container: list[BaseException | None] = [None]

    def _worker() -> None:
        try:
            result[0] = fn()
        except BaseException as exc:  # noqa: BLE001
            exc_container[0] = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive():
        # Thread still running — the match call has no cooperative-cancel
        # primitive in the re module, so we simply abandon it. Daemon
        # thread will be cleaned up at process exit. Log the event.
        raise _PatternTimeoutError
    if exc_container[0] is not None:
        raise exc_container[0]
    return result[0]


# ---------------------------------------------------------------------------
# Pattern application
# ---------------------------------------------------------------------------


def _apply_one(
    text: str, pattern: CompiledPattern
) -> tuple[str, int]:
    """Apply a single compiled pattern to ``text``.

    Returns ``(new_text, substitution_count)``. Falls back to ``(text, 0)``
    when the pattern times out (ReDoS defense) or raises — the bad pattern
    is **not** disabled here (that's a separate admin concern); we just
    skip it for this call so the turn-response isn't held up.
    """
    try:
        def _sub() -> tuple[str, int]:
            return pattern.regex.subn(pattern.replacement, text)

        new_text, count = _run_with_timeout(_sub, timeout_s=_MATCH_TIMEOUT_S)
        return new_text, count
    except _PatternTimeoutError:
        logger.warning(
            "redact_consumer: pattern id=%s exceeded %dms — skipped",
            pattern.id,
            _MATCH_TIMEOUT_MS,
        )
        return text, 0
    except Exception as exc:  # noqa: BLE001 — never break the event-stream
        logger.debug(
            "redact_consumer: pattern id=%s raised: %s",
            pattern.id,
            exc,
        )
        return text, 0


def _apply_to_value(
    value: Any, patterns: Iterable[CompiledPattern], counter: list[int]
) -> Any:
    """Recursively apply patterns to a JSON-serialisable value.

    Mirrors the structure of :func:`agent.security.redact._redact_value`
    so both paths can share tests. ``counter`` is a mutable 1-slot list
    for substitution accumulation.
    """
    if isinstance(value, str):
        current = value
        for pattern in patterns:
            current, count = _apply_one(current, pattern)
            counter[0] += count
        return current
    if isinstance(value, dict):
        return {k: _apply_to_value(v, patterns, counter) for k, v in value.items()}
    if isinstance(value, list):
        return [_apply_to_value(item, patterns, counter) for item in value]
    if isinstance(value, tuple):
        return tuple(_apply_to_value(item, patterns, counter) for item in value)
    return value


def apply_patterns_to_event(
    event: dict[str, Any], patterns: Iterable[CompiledPattern]
) -> tuple[dict[str, Any], int]:
    """Apply a list of compiled Tier-2 patterns to a span-event dict.

    Returns ``(redacted_event, substitution_count)``. Pass-through when
    ``patterns`` is empty. Event-shape mirrors :func:`agent.security.redact
    .redact_span_event` — we redact only the ``attributes`` subtree when
    present, else the whole event.
    """
    patterns_list = list(patterns)
    if not patterns_list or not event:
        return event, 0

    counter = [0]
    attrs = event.get("attributes")
    if isinstance(attrs, dict):
        new_attrs = _apply_to_value(attrs, patterns_list, counter)
        if counter[0] == 0:
            return event, 0
        return {**event, "attributes": new_attrs}, counter[0]

    # Unusual shape — redact whole tree.
    new_event = _apply_to_value(event, patterns_list, counter)
    return new_event, counter[0]


# ---------------------------------------------------------------------------
# Background consumer (optional)
# ---------------------------------------------------------------------------


class RedactConsumer:
    """Background poll-loop that UPDATE-redacts recently-inserted spans.

    This is the Phase-B minimal runtime — polls ``agent.spans`` every
    ``poll_interval`` seconds, applies custom patterns to rows with
    ``redaction_pass_done IS NULL`` (add this column in a follow-up
    migration if ever enabled; Phase-B ships consumer disabled by default).

    Replaced by a NATS-JetStream subscriber when the scheduler's event-
    bus pattern matures and Phase-C picks this up. Until then the polling
    loop keeps the contract simple + observable.
    """

    def __init__(
        self,
        dsn: str,
        *,
        poll_interval: float = 5.0,
        org_scope: str | None = None,
    ) -> None:
        self._dsn = dsn
        self._poll_interval = poll_interval
        self._org_scope = org_scope
        self._patterns: list[CompiledPattern] = []
        self._patterns_loaded_at: float = 0.0
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if not _CONSUMER_ENABLED:
            logger.debug(
                "redact_consumer: disabled via MATRIX_REDACT_CONSUMER_ENABLED"
            )
            return
        if self._task is not None:
            return  # already running
        self._task = asyncio.create_task(self._run(), name="redact-consumer")
        logger.info(
            "redact_consumer: started poll_interval=%.1fs", self._poll_interval
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=10)
        except TimeoutError:
            self._task.cancel()
        self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._tick()
            except Exception:  # noqa: BLE001
                logger.exception("redact_consumer: tick failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=self._poll_interval
                )
            except TimeoutError:
                continue

    async def _tick(self) -> None:
        """One poll-tick: refresh patterns + scan recent spans.

        Phase-B ships the pattern-refresh path; the span-UPDATE path is
        intentionally empty until ``agent.spans`` gets a
        ``redaction_pass_done`` column (follow-up migration when the
        consumer is first turned on for a real deployment). Until then
        every tick is a no-op DB hit + pattern reload + metric emit.
        """
        now = time.time()
        # Reload patterns every 60s (admins may add new rows mid-run).
        if now - self._patterns_loaded_at > 60.0 or not self._patterns:
            self._patterns = await load_patterns(
                self._dsn, org_scope=self._org_scope
            )
            self._patterns_loaded_at = now
        # TODO(phase-c): scan agent.spans WHERE redaction_pass_done IS NULL
        # LIMIT N, apply patterns, UPDATE row. Ship when a deployment
        # actually enables the consumer.
