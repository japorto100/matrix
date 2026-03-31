# Session Consent Cache — exec-12 Phase 2.2
# Per thread_id + tool_name cache for consent decisions.
# Ahead of SOTA: no production framework has this as of March 2026.

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

# Default TTL: 30 minutes (matches working memory TTL)
DEFAULT_CACHE_TTL = 1800


@dataclass
class CachedConsent:
    decision: Literal["allow", "deny"]
    timestamp: float
    expires_at: float


class SessionConsentCache:
    """In-memory consent cache scoped by thread_id + tool_name.

    Supports four user decisions:
    - allow_once:    no cache entry
    - allow_session: cache "allow" for this thread + tool
    - deny:          no cache entry
    - deny_session:  cache "deny" for this thread + tool
    """

    def __init__(self, ttl_seconds: float = DEFAULT_CACHE_TTL) -> None:
        self._ttl = ttl_seconds
        # {thread_id: {tool_name: CachedConsent}}
        self._store: dict[str, dict[str, CachedConsent]] = {}

    def get(self, thread_id: str, tool_name: str) -> Literal["allow", "deny"] | None:
        """Check if a cached consent exists. Returns None if no cache or expired."""
        thread_cache = self._store.get(thread_id)
        if thread_cache is None:
            return None

        entry = thread_cache.get(tool_name)
        if entry is None:
            return None

        if time.monotonic() > entry.expires_at:
            del thread_cache[tool_name]
            if not thread_cache:
                del self._store[thread_id]
            return None

        return entry.decision

    def grant(self, thread_id: str, tool_name: str) -> None:
        """Cache an 'allow' decision for this session."""
        self._set(thread_id, tool_name, "allow")

    def deny(self, thread_id: str, tool_name: str) -> None:
        """Cache a 'deny' decision for this session."""
        self._set(thread_id, tool_name, "deny")

    def revoke(self, thread_id: str, tool_name: str | None = None) -> None:
        """Revoke cached consent. If tool_name is None, revoke all for this thread."""
        if tool_name is None:
            self._store.pop(thread_id, None)
        else:
            thread_cache = self._store.get(thread_id)
            if thread_cache:
                thread_cache.pop(tool_name, None)
                if not thread_cache:
                    del self._store[thread_id]

    def clear(self) -> None:
        """Clear entire cache."""
        self._store.clear()

    def _set(self, thread_id: str, tool_name: str, decision: Literal["allow", "deny"]) -> None:
        now = time.monotonic()
        entry = CachedConsent(
            decision=decision,
            timestamp=now,
            expires_at=now + self._ttl,
        )
        if thread_id not in self._store:
            self._store[thread_id] = {}
        self._store[thread_id][tool_name] = entry


# ── Singleton ──────────────────────────────────────────────────────────────

_cache: SessionConsentCache | None = None


def get_consent_cache() -> SessionConsentCache:
    global _cache
    if _cache is None:
        _cache = SessionConsentCache()
    return _cache
