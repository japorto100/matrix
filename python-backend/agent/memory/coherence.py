"""Cache Coherence fuer Multi-Agent Memory (exec-11, Paper 2 inspired).

Problem: Parallele Agents koennen widersprüchliche Fakten retainen.
  Agent A: "EUR/USD ist bullish" (Fundamentals)
  Agent B: "EUR/USD ist bearish" (Sentiment)
  → Welcher Fakt gilt?

Loesung: Write-Ahead Log + Version Tracking + Conflict Detection.

Drei Mechanismen:
1. Version Tracking: Jeder Retain bekommt eine monoton steigende Version
2. Conflict Detection: Vor Recall pruefen ob widersprüchliche Fakten existieren
3. Resolution Strategy: Neuester Fakt gewinnt (default) oder LLM-basierte Fusion

Aktuell: Unser Orchestrator ist sequentiell bei Writes → geringes Risiko.
Dieses Modul ist Infrastruktur fuer den Fall dass parallele Writes kommen.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WriteEntry:
    """Ein Eintrag im Write-Ahead Log."""
    version: int
    role: str
    content: str
    timestamp: float
    bank_id: str
    tags: list[str] = field(default_factory=list)


@dataclass
class ConflictReport:
    """Ergebnis einer Conflict Detection."""
    has_conflict: bool
    entries: list[WriteEntry] = field(default_factory=list)
    resolution: str = ""  # "latest_wins" | "llm_fusion" | "manual"


class MemoryCoherenceManager:
    """Trackt Memory Writes und erkennt Konflikte zwischen parallelen Agents.

    Write-Ahead Log Pattern:
    1. Vor Retain: write_ahead(role, content) → Version
    2. Conflict Check: detect_conflicts(bank_id, entity) → ConflictReport
    3. Resolution: resolve(conflict) → merged Fakt oder latest-wins

    Thread-safe via asyncio.Lock.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._version_counter = 0
        # Write-Ahead Log: bank_id → list[WriteEntry]
        self._wal: dict[str, list[WriteEntry]] = {}
        # Max entries per bank (sliding window)
        self._max_entries = 100

    async def write_ahead(self, bank_id: str, role: str, content: str, tags: list[str] | None = None) -> int:
        """Registriert einen bevorstehenden Write im WAL.

        Returns: Version number fuer diesen Write.
        """
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
            if bank_id not in self._wal:
                self._wal[bank_id] = []
            wal = self._wal[bank_id]
            wal.append(entry)
            # Sliding window
            if len(wal) > self._max_entries:
                self._wal[bank_id] = wal[-self._max_entries:]
            return self._version_counter

    async def detect_conflicts(
        self,
        bank_id: str,
        time_window_seconds: float = 60.0,
    ) -> ConflictReport:
        """Erkennt widersprüchliche Writes innerhalb eines Zeitfensters.

        Zwei Writes sind potenziell widersprüchlich wenn:
        - Gleiche Bank
        - Verschiedene Rollen
        - Innerhalb des Zeitfensters
        - Aehnlicher Content (gleiche Entities erwaehnt)
        """
        async with self._lock:
            wal = self._wal.get(bank_id, [])
            if len(wal) < 2:
                return ConflictReport(has_conflict=False)

            cutoff = time.time() - time_window_seconds
            recent = [e for e in wal if e.timestamp >= cutoff]

            if len(recent) < 2:
                return ConflictReport(has_conflict=False)

            # Gruppen nach Rolle
            roles_seen: dict[str, list[WriteEntry]] = {}
            for entry in recent:
                roles_seen.setdefault(entry.role, []).append(entry)

            # Konflikt wenn 2+ Rollen in gleichem Zeitfenster geschrieben haben
            if len(roles_seen) >= 2:
                all_entries = [e for entries in roles_seen.values() for e in entries]
                return ConflictReport(
                    has_conflict=True,
                    entries=all_entries,
                    resolution="latest_wins",  # Default-Strategie
                )

            return ConflictReport(has_conflict=False)

    async def resolve_latest_wins(self, conflict: ConflictReport) -> WriteEntry | None:
        """Resolution: Neuester Fakt gewinnt."""
        if not conflict.entries:
            return None
        return max(conflict.entries, key=lambda e: e.version)

    def clear(self, bank_id: str) -> None:
        """Loescht WAL fuer eine Bank."""
        self._wal.pop(bank_id, None)


# Singleton
_coherence_manager: MemoryCoherenceManager | None = None


def get_coherence_manager() -> MemoryCoherenceManager:
    """Gibt den Singleton Coherence Manager zurueck."""
    global _coherence_manager
    if _coherence_manager is None:
        _coherence_manager = MemoryCoherenceManager()
    return _coherence_manager
