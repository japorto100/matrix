# BTE/DRS Guards per AGENT_ARCHITECTURE.md Sek. 4
# Deterministic rule engine — no LLM, reproducible scoring

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class VerifiedMarker:
    """Marker passed by Verifier (simplified)."""

    marker_id: str
    category: str
    value: float
    evidence: str


@dataclass
class GuardResult:
    """Output of Deterministic Guard."""

    total_score: float
    threshold_exceeded: bool
    breakdown: dict[str, float]
    confidence: float
    flags: list[str]


class DeterministicGuard(Protocol):
    """Protocol for BTE/DRS-style guards."""

    def calculate_score(self, verified_markers: list[VerifiedMarker]) -> GuardResult: ...
