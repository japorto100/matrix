"""Cache adapter layer for memory service.

ENV:
    MEMORY_CACHE_PROVIDER=local|redis|valkey   — primary switch
    PYTHON_REDIS_URL=redis://...               — Python-backend Redis (takes precedence)
    MEMORY_REDIS_URL=redis://...               — Redis URL (provider=redis)
    MEMORY_VALKEY_URL=redis://...              — Valkey URL (provider=valkey)

Key namespace: tradeview:m1:{indicator}:{symbol}:{tf}
TTL classes: 300s (live data), 900s (indicators), 3600s (snapshots)
"""
from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class CacheAdapter(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def ping(self) -> bool:
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        ...


# ---------------------------------------------------------------------------
# LRU in-process adapter (no external dependency)
# ---------------------------------------------------------------------------

class LRUCacheAdapter(CacheAdapter):
    """Thread-safe LRU cache using a simple dict with TTL tracking."""

    def __init__(self, max_size: int = 4096) -> None:
        self._max_size = max_size
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)

    async def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        if len(self._store) >= self._max_size and key not in self._store:
            # Evict oldest expired entry first, then oldest entry
            now = time.monotonic()
            expired = [k for k, (_, exp) in self._store.items() if now > exp]
            if expired:
                del self._store[expired[0]]
            elif self._store:
                del self._store[next(iter(self._store))]
        self._store[key] = (value, time.monotonic() + ttl_seconds)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def ping(self) -> bool:
        return True

    @property
    def backend_name(self) -> str:
        return "lru"


# ---------------------------------------------------------------------------
# Redis adapter (optional, requires redis>=5.0.0)
# ---------------------------------------------------------------------------

class RedisCacheAdapter(CacheAdapter):
    def __init__(self, url: str, backend_name: str = "redis") -> None:
        import json
        import redis.asyncio as aioredis  # type: ignore[import-untyped]
        # Explicit Any so that async methods (ping, get, set, delete, setex)
        # are correctly treated as awaitable regardless of redis-py stub versions.
        self._client: Any = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
        self._json = json
        self._backend_name = backend_name

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._client.get(key)
        if raw is None:
            return None
        try:
            return self._json.loads(raw)
        except Exception:
            return raw

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        serialized = self._json.dumps(value)
        await self._client.setex(key, ttl_seconds, serialized)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    @property
    def backend_name(self) -> str:
        return self._backend_name


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_cache_adapter() -> CacheAdapter:
    """Return appropriate cache adapter based on ENV configuration."""
    provider = os.getenv("MEMORY_CACHE_PROVIDER", "").strip().lower()
    if provider in ("redis", "valkey"):
        # PYTHON_REDIS_URL takes precedence — dedicated Python Redis (:6380).
        # Falls back to provider-specific URL (MEMORY_VALKEY_URL / MEMORY_REDIS_URL).
        url_key = "MEMORY_VALKEY_URL" if provider == "valkey" else "MEMORY_REDIS_URL"
        redis_url = os.getenv("PYTHON_REDIS_URL") or os.getenv(url_key, "")
        if not redis_url:
            import logging
            logging.getLogger(__name__).warning(
                "MEMORY_CACHE_PROVIDER=%s but no URL configured (PYTHON_REDIS_URL / %s). "
                "Falling back to local LRU cache.",
                provider, url_key,
            )
            return LRUCacheAdapter()
        return RedisCacheAdapter(redis_url, backend_name=provider)
    return LRUCacheAdapter()


# ---------------------------------------------------------------------------
# Key builder helpers
# ---------------------------------------------------------------------------

def cache_key(indicator: str, symbol: str, timeframe: str) -> str:
    """Build canonical cache key: tradeview:m1:{indicator}:{symbol}:{timeframe}"""
    return f"tradeview:m1:{indicator}:{symbol}:{timeframe}"


# TTL constants (seconds)
TTL_LIVE = 300       # 5 min — real-time quotes, streaming data
TTL_INDICATOR = 900  # 15 min — computed indicators
TTL_SNAPSHOT = 3600  # 1 hour — analysis snapshots, KG sync
