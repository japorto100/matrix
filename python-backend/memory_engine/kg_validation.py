"""Wisdom/GraphMERT validation contracts for global KG claims.

Feature 017 treats GraphMERT as an optional asynchronous Slow-Lane validator.
This module defines the stable contract before a real checkpoint is wired in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from memory_engine.global_kg import EvidenceRef


@dataclass(frozen=True)
class TripleValidationInput:
    """Normalized triple passed to a Wisdom/GraphMERT-style validator."""

    subject_key: str
    predicate: str
    object_key: str
    lane: str = "slow"
    evidence: tuple[EvidenceRef, ...] = ()
    valid_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TripleValidationResult:
    """Validator output stored as claim adjudication metadata."""

    validator: str
    validator_version: str
    score: float | None
    decision: str
    reason: str
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    contradiction_refs: tuple[str, ...] = ()
    corroboration_count: int = 0

    def as_metadata(self) -> dict[str, object]:
        return {
            "validator": self.validator,
            "validator_version": self.validator_version,
            "score": self.score,
            "decision": self.decision,
            "reason": self.reason,
            "checked_at": self.checked_at.isoformat(),
            "contradiction_refs": list(self.contradiction_refs),
            "corroboration_count": self.corroboration_count,
        }


class TripleValidator(Protocol):
    """Async-compatible protocol for future GraphMERT/checkpoint adapters."""

    async def validate(self, item: TripleValidationInput) -> TripleValidationResult:
        """Return plausibility/adjudication metadata for one triple."""


class NoOpGraphMERTValidator:
    """Explicit placeholder when no checkpoint is configured."""

    version = "graphmert:no-checkpoint"

    async def validate(self, item: TripleValidationInput) -> TripleValidationResult:
        del item
        return TripleValidationResult(
            validator="graphmert",
            validator_version=self.version,
            score=None,
            decision="skipped",
            reason="no_graphmert_checkpoint_configured",
        )


class RuleBasedWisdomValidator:
    """Deterministic guardrail validator used until a real model wins evals."""

    version = "rules:2026-04-27"

    async def validate(self, item: TripleValidationInput) -> TripleValidationResult:
        if item.lane.strip().lower() == "fast":
            return TripleValidationResult(
                validator="rules",
                validator_version=self.version,
                score=None,
                decision="skipped",
                reason="fast_lane_not_validated_inline",
                corroboration_count=len(item.evidence),
            )
        if not item.evidence:
            return TripleValidationResult(
                validator="rules",
                validator_version=self.version,
                score=0.0,
                decision="reject",
                reason="missing_evidence",
            )
        if not item.subject_key or not item.predicate or not item.object_key:
            return TripleValidationResult(
                validator="rules",
                validator_version=self.version,
                score=0.0,
                decision="reject",
                reason="incomplete_triple",
                corroboration_count=len(item.evidence),
            )
        if item.subject_key == item.object_key:
            return TripleValidationResult(
                validator="rules",
                validator_version=self.version,
                score=0.05,
                decision="reject",
                reason="self_relation_hard_negative",
                corroboration_count=len(item.evidence),
            )
        score = min(0.95, 0.55 + (0.1 * len(item.evidence)))
        return TripleValidationResult(
            validator="rules",
            validator_version=self.version,
            score=score,
            decision="support" if score >= 0.65 else "needs_review",
            reason="evidence_backed_structural_claim",
            corroboration_count=len(item.evidence),
        )


def supports_slow_lane_promotion(
    result: TripleValidationResult,
    *,
    min_score: float = 0.65,
) -> bool:
    """Return whether a Wisdom result may support, not force, promotion."""

    return (
        result.decision == "support"
        and result.score is not None
        and result.score >= min_score
        and not result.contradiction_refs
        and result.corroboration_count > 0
    )
