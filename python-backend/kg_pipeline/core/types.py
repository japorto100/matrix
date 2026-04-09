"""KG types (Phase 2 — Skeleton).

These dataclasses will be filled in when adopting paperwatcher kg-module.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entity:
    """Stub. Phase 2: id, label, type, mentions, confidence, ..."""

    id: str = ""
    label: str = ""
    type: str = ""
    confidence: float = 0.0


@dataclass
class Relation:
    """Stub. Phase 2: subject, predicate, object, confidence, evidence."""

    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = 0.0


@dataclass
class ExtractionResult:
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
