"""KG extraction types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entity:
    """Candidate canonical entity extracted from an evidence chunk."""

    id: str = ""
    label: str = ""
    type: str = "unknown"
    confidence: float = 0.0
    mentions: list[str] = field(default_factory=list)


@dataclass
class Relation:
    """Candidate relation/claim extracted from an evidence chunk."""

    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = 0.0
    evidence: str = ""
    doc_id: str = ""
    lane: str = "fast"


@dataclass
class ExtractionResult:
    doc_id: str = ""
    entities: list[Entity] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    skipped: bool = False
    extractor: str = "heuristic"
    warnings: list[str] = field(default_factory=list)
