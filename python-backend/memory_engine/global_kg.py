"""Global/domain KG claim helpers for Feature 017.

This module is intentionally separate from Hindsight/MemPalace memory. It owns
stable IDs and scoring primitives for world/trading/geopolitical KG claims; the
database migration stores those claims in `agent.kg_*` tables.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

_KEY_CHARS = re.compile(r"[^a-z0-9]+")


def normalize_entity_key(value: str) -> str:
    """Normalize entity text into a deterministic canonical key."""

    normalized = _KEY_CHARS.sub(":", value.strip().lower()).strip(":")
    return normalized or "unknown"


def stable_hash(*parts: object, length: int = 24) -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


@dataclass(frozen=True)
class EntityRef:
    key: str
    entity_type: str = "unknown"
    name: str | None = None

    @property
    def entity_id(self) -> str:
        return f"ent_{stable_hash(self.key)}"

    @classmethod
    def from_name(cls, name: str, *, entity_type: str = "unknown") -> EntityRef:
        return cls(
            key=normalize_entity_key(name),
            entity_type=entity_type,
            name=name.strip() or None,
        )


@dataclass(frozen=True)
class EvidenceRef:
    source_layer: str
    source_ref: str
    source_uri: str | None = None
    content_hash: str | None = None
    quote: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def evidence_id(self) -> str:
        return f"ev_{stable_hash(self.source_layer, self.source_ref, self.content_hash)}"


@dataclass(frozen=True)
class ClaimProposal:
    subject: EntityRef
    predicate: str
    valid_from: datetime
    valid_to: datetime | None = None
    object_entity: EntityRef | None = None
    object_value: dict[str, Any] | None = None
    lane: str = "fast"
    status: str = "proposed"
    confidence: float = 0.0
    evidence: tuple[EvidenceRef, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.object_entity is None and self.object_value is None:
            raise ValueError("ClaimProposal requires object_entity or object_value")
        if self.lane not in {"fast", "slow"}:
            raise ValueError("lane must be fast or slow")
        if self.status not in {"proposed", "promoted", "rejected", "superseded"}:
            raise ValueError("invalid claim status")

    @property
    def object_key(self) -> str:
        if self.object_entity is not None:
            return self.object_entity.key
        return stable_hash(self.object_value)

    @property
    def conflict_key(self) -> str:
        return build_conflict_key(self.subject.key, self.predicate, self.object_key)

    @property
    def claim_id(self) -> str:
        evidence_ids = [e.evidence_id for e in self.evidence]
        return f"claim_{stable_hash(self.conflict_key, self.valid_from, self.valid_to, evidence_ids)}"

    @property
    def claim_text(self) -> str:
        obj = self.object_entity.name if self.object_entity else json.dumps(self.object_value, sort_keys=True)
        subject = self.subject.name or self.subject.key
        return f"{subject} {self.predicate} {obj}"

    def projection_payload(self) -> dict[str, Any]:
        """NornicDB/nonicdb projection payload for a rebuildable outbox event."""

        return {
            "claim_id": self.claim_id,
            "subject": {
                "entity_id": self.subject.entity_id,
                "canonical_key": self.subject.key,
                "entity_type": self.subject.entity_type,
                "name": self.subject.name,
            },
            "predicate": self.predicate,
            "object": {
                "entity_id": self.object_entity.entity_id if self.object_entity else None,
                "canonical_key": self.object_entity.key if self.object_entity else None,
                "entity_type": self.object_entity.entity_type if self.object_entity else None,
                "name": self.object_entity.name if self.object_entity else None,
                "value": self.object_value,
            },
            "lane": self.lane,
            "status": self.status,
            "confidence": self.confidence,
            "valid_from": self.valid_from.astimezone(UTC).isoformat(),
            "valid_to": self.valid_to.astimezone(UTC).isoformat() if self.valid_to else None,
            "evidence_ids": [e.evidence_id for e in self.evidence],
            "metadata": self.metadata,
        }


def build_conflict_key(subject_key: str, predicate: str, object_key: str) -> str:
    return "::".join(
        (
            normalize_entity_key(subject_key),
            normalize_entity_key(predicate),
            normalize_entity_key(object_key),
        )
    )


def decay_score(
    semantic_similarity: float,
    *,
    now: datetime,
    last_accessed: datetime | None = None,
    valid_to: datetime | None = None,
    access_half_life_days: float = 90.0,
    valid_half_life_days: float = 90.0,
) -> float:
    """Combine semantic score with recency and validity-end decay."""

    def age_days(ts: datetime | None) -> float:
        if ts is None:
            return 0.0
        return max(0.0, (now - ts).total_seconds() / 86_400.0)

    access_lambda = math.log(2.0) / access_half_life_days
    valid_lambda = math.log(2.0) / valid_half_life_days
    access_age = age_days(last_accessed)
    valid_age = age_days(valid_to) if valid_to and valid_to < now else 0.0
    return float(
        semantic_similarity
        * math.exp(-access_lambda * access_age)
        * math.exp(-valid_lambda * valid_age)
    )
