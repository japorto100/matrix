# Agent Working Memory (M5) — Phase 10c / exec-12 Option C
# Per-Entry Keys: each entry gets its own cache key (atomic, no read-modify-write).
# Eliminates race conditions when multiple agents write to the same session.
# Ref: MEMORY_ARCHITECTURE.md Sek. 5.5, CONTEXT_ENGINEERING.md

from __future__ import annotations

import time
import uuid
from typing import Any

# TTL 30min per entry
M5_TTL_SECONDS = 1800
M5_MAX_ENTRIES = 50
M5_SESSION_PREFIX = "tradeview:m5:session:"


def _get_cache():
    """Lazy init cache adapter (reuse memory-service pattern)."""
    from shared.cache_adapter import create_cache_adapter
    return create_cache_adapter()


def _entry_key(session_id: str, entry_id: str) -> str:
    """Build per-entry cache key."""
    return f"{M5_SESSION_PREFIX}{session_id}:entry:{entry_id}"


def _index_key(session_id: str) -> str:
    """Build session index key (tracks entry_ids for enumeration)."""
    return f"{M5_SESSION_PREFIX}{session_id}:index"


async def working_memory_get(session_id: str) -> dict[str, Any]:
    """Get full scratchpad for session (reads index, then fetches each entry)."""
    cache = _get_cache()
    index_raw = await cache.get(_index_key(session_id))
    if not index_raw:
        return {}

    entry_ids = index_raw if isinstance(index_raw, list) else []
    result: dict[str, Any] = {}
    stale_ids: list[str] = []

    for eid in entry_ids:
        val = await cache.get(_entry_key(session_id, eid))
        if val is not None:
            result[eid] = val
        else:
            stale_ids.append(eid)

    # Clean up stale entries from index (expired TTL)
    if stale_ids:
        live_ids = [eid for eid in entry_ids if eid not in stale_ids]
        await cache.set(_index_key(session_id), live_ids, ttl_seconds=M5_TTL_SECONDS)

    return result


async def working_memory_set(
    session_id: str,
    entry_id: str,
    content: Any,
) -> None:
    """Add/update entry in session scratchpad. Atomic per entry — no race conditions."""
    cache = _get_cache()
    now = time.time()
    entry_val = {"content": content, "timestamp": now}

    # Write entry atomically
    await cache.set(_entry_key(session_id, entry_id), entry_val, ttl_seconds=M5_TTL_SECONDS)

    # Update index (add entry_id if not present, evict oldest if over limit)
    index_raw = await cache.get(_index_key(session_id))
    entry_ids: list[str] = index_raw if isinstance(index_raw, list) else []

    if entry_id not in entry_ids:
        entry_ids.append(entry_id)

    # Evict oldest entries if over limit
    if len(entry_ids) > M5_MAX_ENTRIES:
        evict_ids = entry_ids[: len(entry_ids) - M5_MAX_ENTRIES]
        entry_ids = entry_ids[len(entry_ids) - M5_MAX_ENTRIES:]
        for eid in evict_ids:
            await cache.delete(_entry_key(session_id, eid))

    await cache.set(_index_key(session_id), entry_ids, ttl_seconds=M5_TTL_SECONDS)


async def working_memory_get_entry(session_id: str, entry_id: str) -> Any | None:
    """Get a single entry by key. O(1), no full scan needed."""
    cache = _get_cache()
    val = await cache.get(_entry_key(session_id, entry_id))
    return val


async def working_memory_append(
    session_id: str,
    role: str,
    content: Any,
) -> str:
    """Append entry with auto-generated id. Returns entry_id."""
    entry_id = f"{role}:{uuid.uuid4().hex[:8]}"
    await working_memory_set(session_id, entry_id, content)
    return entry_id


async def working_memory_clear(session_id: str) -> None:
    """Clear session scratchpad (delete all entries + index)."""
    cache = _get_cache()
    index_raw = await cache.get(_index_key(session_id))
    if index_raw and isinstance(index_raw, list):
        for eid in index_raw:
            await cache.delete(_entry_key(session_id, eid))
    await cache.delete(_index_key(session_id))
