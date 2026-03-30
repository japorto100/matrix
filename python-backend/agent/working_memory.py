# Agent Working Memory (M5) — Phase 10c
# Redis Hash per Session, TTL 30min, Oldest-first Eviction
# Ref: MEMORY_ARCHITECTURE.md Sek. 5.5, CONTEXT_ENGINEERING.md

from __future__ import annotations

import json
import time
import uuid
from typing import Any

# TTL 30min per plan
M5_TTL_SECONDS = 1800
M5_MAX_ENTRIES = 50
M5_KEY_PREFIX = "tradeview:m5:session:"


def _get_cache():
    """Lazy init cache adapter (reuse memory-service pattern)."""
    from shared.cache_adapter import create_cache_adapter
    return create_cache_adapter()


async def working_memory_get(session_id: str) -> dict[str, Any]:
    """Get full scratchpad for session."""
    cache = _get_cache()
    key = f"{M5_KEY_PREFIX}{session_id}"
    raw = await cache.get(key)
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw) if isinstance(raw, str) else {}
    except Exception:
        return {}


async def working_memory_set(
    session_id: str,
    entry_id: str,
    content: Any,
) -> None:
    """Add/update entry in session scratchpad. Oldest-first eviction when over limit."""
    cache = _get_cache()
    key = f"{M5_KEY_PREFIX}{session_id}"
    data = await working_memory_get(session_id)
    now = time.time()
    data[entry_id] = {"content": content, "timestamp": now}
    # Evict oldest if over limit
    if len(data) > M5_MAX_ENTRIES:
        sorted_entries = sorted(data.items(), key=lambda x: x[1].get("timestamp", 0))
        for k, _ in sorted_entries[: len(data) - M5_MAX_ENTRIES]:
            del data[k]
    await cache.set(key, data, ttl_seconds=M5_TTL_SECONDS)


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
    """Clear session scratchpad."""
    cache = _get_cache()
    key = f"{M5_KEY_PREFIX}{session_id}"
    await cache.delete(key)
