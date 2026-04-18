"""Credential-pool ABC + single-key adapter (exec-hermes §4.4).

Abstraction over per-(user, provider) API-key management that the agent
harness can consult when the error classifier emits a rotation recovery
strategy. Pairs with :class:`agent.resilience.error_classifier`:

- ``classify_error(exc).recovery == RecoveryStrategy.rotate_immediately``
  (auth / billing) → call :meth:`CredentialPool.mark_auth_failed` or
  :meth:`mark_exhausted` and re-acquire.
- ``RecoveryStrategy.backoff_then_rotate`` (rate_limit) → same, with a
  shorter cooldown.
- ``RecoveryStrategy.compress`` / ``retry`` / ``fallback`` → no pool
  interaction (handled by context engine / harness fallback logic).

**Scope note.** The hermes reference
(``_ref/hermes-agent/agent/credential_pool.py``, 1431 LOC) bundles OAuth
token refresh, JWT claim decoding, Codex CLI integration, and provider-
specific portal logic. Matrix runs per-user API keys out of
``agent.user_credentials`` (one row per user+provider today), so the
port is deliberately **minimum-viable**:

- ABC with four coarse lifecycle methods.
- :class:`SingleKeyCredentialPool` concrete impl wrapping
  :func:`agent.security.credentials.get_user_api_key`. Tracks
  exhaustion/auth-failure in-memory; when the one key is blocked,
  ``acquire`` returns ``None`` and the caller surfaces a user-facing
  error. No real rotation yet — that lands when the DB schema grows
  a multi-key-per-(user,provider) table.
- :func:`apply_recovery` helper — one call translates a
  ``ClassificationResult`` into the matching pool method call.

Thread-safety: not thread-safe (plain dicts, matches the ``asyncio``
single-loop runtime of ``agent/graph/*``). Wrap with ``asyncio.Lock`` at
the call site if we ever invoke pool methods from multiple event loops.
"""
from __future__ import annotations

import enum
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from agent.resilience.error_classifier import ClassificationResult, FailoverReason

logger = logging.getLogger(__name__)

__all__ = [
    "CredentialStatus",
    "Credential",
    "CredentialPool",
    "SingleKeyCredentialPool",
    "apply_recovery",
    "get_credential_pool",
    "reset_credential_pool",
]


# Default cooldown windows (seconds). Caller can override via
# apply_recovery's optional args or by calling mark_* directly.
RATE_LIMIT_COOLDOWN_SECONDS = 60 * 60           # 1 h — matches provider 429 reset
BILLING_COOLDOWN_SECONDS = 24 * 60 * 60         # 24 h — billing errors rarely resolve fast
SERVER_ERROR_COOLDOWN_SECONDS = 5 * 60          # 5 min — short cooldown for 5xx


class CredentialStatus(enum.Enum):
    """Current health of a credential per the pool's bookkeeping."""

    ok = "ok"                      # usable
    exhausted = "exhausted"        # rate-limited / billing — retry after TTL
    auth_failed = "auth_failed"    # invalid key — do not retry without user action
    unknown = "unknown"            # not yet observed


@dataclass(frozen=True)
class Credential:
    """A single credential the harness can use for a provider call.

    ``key_id`` is an opaque SHA-256 prefix of the plaintext key so logs and
    metrics can identify a credential without leaking it. ``api_key`` is
    the plaintext value the caller passes to the provider SDK — never log
    it.
    """

    provider: str
    user_id: str
    key_id: str
    api_key: str
    status: CredentialStatus = CredentialStatus.ok
    exhausted_until: float = 0.0    # epoch seconds; 0 = not exhausted
    last_used: float = 0.0

    @property
    def is_usable(self) -> bool:
        if self.status is not CredentialStatus.ok:
            return False
        if self.exhausted_until > time.time():
            return False
        return True


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------

class CredentialPool(ABC):
    """Abstract contract for per-(user, provider) credential management.

    Subclasses implement the four lifecycle methods. The agent harness
    consults the pool in two places:

    1. Before an LLM call: ``credential = await pool.acquire(user, prov)``
       → if ``None``, no usable key (surface user-visible error).
    2. After an LLM call fails with a rotation-class recovery: call
       :func:`apply_recovery` or the corresponding ``mark_*`` method to
       update state, then try ``acquire`` again.
    """

    @abstractmethod
    async def acquire(
        self, user_id: str, provider: str
    ) -> Credential | None:
        """Return the next usable credential, or ``None`` if none available."""

    @abstractmethod
    async def mark_exhausted(
        self,
        credential: Credential,
        *,
        reset_seconds: float = RATE_LIMIT_COOLDOWN_SECONDS,
    ) -> None:
        """Flag a credential as rate-limited / billing-exhausted.

        ``reset_seconds`` controls the cooldown before ``acquire`` will
        return it again. Providers sometimes expose a precise
        ``x-ratelimit-reset``; callers can pass that through.
        """

    @abstractmethod
    async def mark_auth_failed(self, credential: Credential) -> None:
        """Flag a credential as invalid — do not retry without user action."""

    @abstractmethod
    async def mark_success(self, credential: Credential) -> None:
        """Reset any exhausted / auth-failed state — the credential just worked."""


# ---------------------------------------------------------------------------
# SingleKey concrete impl
# ---------------------------------------------------------------------------

# Type alias for dependency injection — tests pass a sync lambda; production
# passes ``agent.security.credentials.get_user_api_key``.
GetKeyFn = Callable[[str, str], Awaitable[str | None]]


async def _default_get_user_api_key(user_id: str, provider: str) -> str | None:
    # Local import so ``credential_pool`` doesn't hard-import the DB layer at
    # module load (tests can construct SingleKeyCredentialPool without psycopg).
    from agent.security.credentials import get_user_api_key

    return await get_user_api_key(user_id, provider)


class SingleKeyCredentialPool(CredentialPool):
    """Matrix current reality: one key per ``(user, provider)`` in the
    ``agent.user_credentials`` table. No rotation — when the single key is
    marked exhausted or auth-failed, ``acquire`` returns ``None`` until the
    cooldown expires (exhausted) or the user explicitly replaces the key
    (auth-failed).

    This is the migration target: callers start depending on
    :class:`CredentialPool` now, and when the DB grows a multi-key schema we
    swap the impl without touching call-sites.
    """

    def __init__(self, get_key_fn: GetKeyFn | None = None) -> None:
        self._get_key_fn: GetKeyFn = get_key_fn or _default_get_user_api_key
        # (user_id, provider) → status bookkeeping.
        self._status: dict[tuple[str, str], CredentialStatus] = {}
        # (user_id, provider) → epoch-seconds when the exhaustion TTL ends.
        self._exhausted_until: dict[tuple[str, str], float] = {}
        # (user_id, provider) → last observed key_id, so we can detect when
        # the underlying key was replaced by the user and reset stale state.
        self._last_key_ids: dict[tuple[str, str], str] = {}

    async def acquire(
        self, user_id: str, provider: str
    ) -> Credential | None:
        key = (user_id, provider)

        # Step 1: fetch current key. If no key at all → nothing to give.
        api_key = await self._get_key_fn(user_id, provider)
        if not api_key:
            return None
        key_id = _hash_key(api_key)

        # Step 2: auto-reset state if the underlying key value changed since
        # last acquire. This MUST run before the auth_failed/exhausted
        # checks — otherwise a user who replaces a previously-rejected key
        # stays permanently blocked by stale bookkeeping.
        last_key_id = self._last_key_ids.get(key)
        if last_key_id is not None and last_key_id != key_id:
            self._status.pop(key, None)
            self._exhausted_until.pop(key, None)
        self._last_key_ids[key] = key_id

        # Step 3: apply bookkeeping blocks. Auth-failed overrides TTL;
        # exhausted blocks until the cooldown expires.
        status = self._status.get(key, CredentialStatus.unknown)
        if status is CredentialStatus.auth_failed:
            return None
        if self._exhausted_until.get(key, 0.0) > time.time():
            return None

        return Credential(
            provider=provider,
            user_id=user_id,
            key_id=key_id,
            api_key=api_key,
            status=CredentialStatus.ok,
            last_used=time.time(),
        )

    async def mark_exhausted(
        self,
        credential: Credential,
        *,
        reset_seconds: float = RATE_LIMIT_COOLDOWN_SECONDS,
    ) -> None:
        key = (credential.user_id, credential.provider)
        self._status[key] = CredentialStatus.exhausted
        self._exhausted_until[key] = time.time() + max(0.0, reset_seconds)
        logger.debug(
            "credential %s marked exhausted for %.0fs",
            credential.key_id, reset_seconds,
        )

    async def mark_auth_failed(self, credential: Credential) -> None:
        key = (credential.user_id, credential.provider)
        self._status[key] = CredentialStatus.auth_failed
        # Auth-fail overrides any remaining exhaustion TTL (the key is
        # dead regardless of time).
        self._exhausted_until.pop(key, None)
        logger.debug("credential %s marked auth_failed", credential.key_id)

    async def mark_success(self, credential: Credential) -> None:
        key = (credential.user_id, credential.provider)
        self._status[key] = CredentialStatus.ok
        self._exhausted_until.pop(key, None)


# ---------------------------------------------------------------------------
# Recovery-strategy dispatcher
# ---------------------------------------------------------------------------

async def apply_recovery(
    pool: CredentialPool,
    credential: Credential,
    classification: ClassificationResult,
    *,
    rate_limit_cooldown: float = RATE_LIMIT_COOLDOWN_SECONDS,
    billing_cooldown: float = BILLING_COOLDOWN_SECONDS,
    server_error_cooldown: float = SERVER_ERROR_COOLDOWN_SECONDS,
) -> None:
    """Translate a :class:`ClassificationResult` into a pool update.

    Mapping:

    - ``FailoverReason.rate_limit`` → ``mark_exhausted(rate_limit_cooldown)``
    - ``FailoverReason.billing``    → ``mark_exhausted(billing_cooldown)``
    - ``FailoverReason.auth``       → ``mark_auth_failed``
    - ``FailoverReason.overloaded`` / ``server_error`` → ``mark_exhausted(short)``
      — treat the credential as transiently unusable rather than dead.
    - ``context_overflow`` / ``timeout`` / ``format_error`` / ``upstream_unavailable``
      / ``unknown`` → no-op (not a credential-level problem).

    Callers should still honour the classification's ``recovery`` field for
    their own retry semantics (backoff, fallback, compress). This helper
    only handles the credential-pool side.
    """
    reason = classification.reason
    if reason is FailoverReason.rate_limit:
        await pool.mark_exhausted(credential, reset_seconds=rate_limit_cooldown)
        return
    if reason is FailoverReason.billing:
        await pool.mark_exhausted(credential, reset_seconds=billing_cooldown)
        return
    if reason is FailoverReason.auth:
        await pool.mark_auth_failed(credential)
        return
    if reason in (FailoverReason.overloaded, FailoverReason.server_error):
        await pool.mark_exhausted(credential, reset_seconds=server_error_cooldown)
        return
    # Everything else — context overflow, timeout, format error, upstream
    # unavailable, unknown — isn't the credential's fault. Leave state alone.


# ---------------------------------------------------------------------------
# Module-level accessor (mirrors llm_node's get_rate_limit_registry pattern)
# ---------------------------------------------------------------------------

_pool: CredentialPool | None = None


def get_credential_pool() -> CredentialPool:
    """Return the process-wide credential-pool singleton (lazy)."""
    global _pool
    if _pool is None:
        _pool = SingleKeyCredentialPool()
    return _pool


def reset_credential_pool() -> None:
    """Testing helper — drop the singleton so the next call rebuilds."""
    global _pool
    _pool = None
