"""Cache coherence for memory_fusion writes.

Kopie aus `agent/memory/coherence.py`, bewusst getrennt damit `agent/memory`
unangetastet bleibt.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class WriteEntry:
    version: int
    role: str
    content: str
    timestamp: float
    bank_id: str
    tags: list[str] = field(default_factory=list)


@dataclass
class ConflictReport:
    has_conflict: bool
    entries: list[WriteEntry] = field(default_factory=list)
    resolution: str = ""


class MemoryCoherenceManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._version_counter = 0
        self._wal: dict[str, list[WriteEntry]] = {}
        self._max_entries = 100

    async def write_ahead(
        self,
        bank_id: str,
        role: str,
        content: str,
        tags: list[str] | None = None,
    ) -> int:
        async with self._lock:
            self._version_counter += 1
            entry = WriteEntry(
                version=self._version_counter,
                role=role,
                content=content[:500],
                timestamp=time.time(),
                bank_id=bank_id,
                tags=tags or [],
            )
            self._wal.setdefault(bank_id, []).append(entry)
            wal = self._wal[bank_id]
            if len(wal) > self._max_entries:
                self._wal[bank_id] = wal[-self._max_entries :]
            return self._version_counter

    async def detect_conflicts(
        self,
        bank_id: str,
        time_window_seconds: float = 60.0,
    ) -> ConflictReport:
        async with self._lock:
            wal = self._wal.get(bank_id, [])
            if len(wal) < 2:
                return ConflictReport(has_conflict=False)

            cutoff = time.time() - time_window_seconds
            recent = [entry for entry in wal if entry.timestamp >= cutoff]
            if len(recent) < 2:
                return ConflictReport(has_conflict=False)

            roles_seen: dict[str, list[WriteEntry]] = {}
            for entry in recent:
                roles_seen.setdefault(entry.role, []).append(entry)

            if len(roles_seen) >= 2:
                all_entries = [entry for entries in roles_seen.values() for entry in entries]
                return ConflictReport(
                    has_conflict=True,
                    entries=all_entries,
                    resolution="latest_wins",
                )
            return ConflictReport(has_conflict=False)

    async def resolve_latest_wins(self, conflict: ConflictReport) -> WriteEntry | None:
        if not conflict.entries:
            return None
        return max(conflict.entries, key=lambda entry: entry.version)

    def clear(self, bank_id: str) -> None:
        self._wal.pop(bank_id, None)


_coherence_manager: MemoryCoherenceManager | None = None


def get_coherence_manager() -> MemoryCoherenceManager:
    global _coherence_manager
    if _coherence_manager is None:
        _coherence_manager = MemoryCoherenceManager()
    return _coherence_manager
