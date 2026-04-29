"""Lightweight entity/relation extractor for local-first KG smoke tests."""

from __future__ import annotations

import hashlib
import re

from kg_pipeline.core.types import Entity, ExtractionResult, Relation

_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}(?:[-_][A-Z0-9]+)*\b")
_ENTITY_TOKEN = r"[A-Z][A-Za-z0-9&-]*"
_ENTITY_PHRASE = rf"{_ENTITY_TOKEN}(?:\s+{_ENTITY_TOKEN}){{0,4}}"
_TITLE_PHRASE_RE = re.compile(rf"\b{_ENTITY_PHRASE}\b")
_STOP_ENTITIES = {
    "A",
    "An",
    "And",
    "As",
    "At",
    "But",
    "For",
    "From",
    "In",
    "It",
    "Of",
    "On",
    "Or",
    "The",
    "This",
    "To",
    "With",
}

_RELATION_PATTERNS: tuple[tuple[str, re.Pattern[str], float], ...] = (
    (
        "SANCTIONED_BY",
        re.compile(
            rf"(?P<object>{_ENTITY_PHRASE})\s+"
            r"(?:sanctioned|sanctions)\s+"
            rf"(?P<subject>{_ENTITY_PHRASE})",
            re.IGNORECASE,
        ),
        0.78,
    ),
    (
        "EXPORTS_TO",
        re.compile(
            rf"(?P<subject>{_ENTITY_PHRASE})\s+"
            r"(?:exports?|ships?)\s+(?:\w+\s+){0,4}?to\s+"
            rf"(?P<object>{_ENTITY_PHRASE})",
            re.IGNORECASE,
        ),
        0.70,
    ),
    (
        "IMPORTS_FROM",
        re.compile(
            rf"(?P<subject>{_ENTITY_PHRASE})\s+"
            r"(?:imports?)\s+(?:\w+\s+){0,4}?from\s+"
            rf"(?P<object>{_ENTITY_PHRASE})",
            re.IGNORECASE,
        ),
        0.70,
    ),
    (
        "OWNS",
        re.compile(
            rf"(?P<subject>{_ENTITY_PHRASE})\s+"
            r"(?:owns?|acquired|controls?)\s+"
            rf"(?P<object>{_ENTITY_PHRASE})",
            re.IGNORECASE,
        ),
        0.72,
    ),
    (
        "AFFECTS",
        re.compile(
            rf"(?P<subject>{_ENTITY_PHRASE})\s+"
            r"(?:affects?|pressures?|disrupts?)\s+"
            rf"(?P<object>{_ENTITY_PHRASE})",
            re.IGNORECASE,
        ),
        0.66,
    ),
    (
        "LOCATED_IN",
        re.compile(
            rf"(?P<subject>{_ENTITY_PHRASE})\s+"
            r"(?:is\s+)?(?:located|based)\s+in\s+"
            rf"(?P<object>{_ENTITY_PHRASE})",
            re.IGNORECASE,
        ),
        0.74,
    ),
)


def _entity_id(label: str) -> str:
    normalized = " ".join(label.lower().split())
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"ent_{digest}"


def _clean_entity(label: str) -> str:
    return " ".join(label.strip(" ,.;:()[]{}").split())


def _entity_type(label: str) -> str:
    upper = label.upper()
    if upper in {"US", "USA", "EU", "UK", "UAE", "UN", "NATO", "OPEC"}:
        return "organization_or_region"
    if any(token in upper for token in ("INC", "CORP", "LTD", "PLC", "LLC", "SA")):
        return "organization"
    if upper in {"OIL", "GAS", "COPPER", "GOLD", "WHEAT", "URANIUM"}:
        return "commodity"
    return "unknown"


def extract_heuristic(text: str, doc_id: str = "") -> ExtractionResult:
    """Extract coarse entity and relation candidates without ML dependencies."""
    entities: dict[str, Entity] = {}
    for match in [*_ACRONYM_RE.finditer(text), *_TITLE_PHRASE_RE.finditer(text)]:
        label = _clean_entity(match.group(0))
        if len(label) < 2 or label in _STOP_ENTITIES:
            continue
        ent_id = _entity_id(label)
        entity = entities.get(ent_id)
        if entity is None:
            entities[ent_id] = Entity(
                id=ent_id,
                label=label,
                type=_entity_type(label),
                confidence=0.55,
                mentions=[label],
            )
        elif label not in entity.mentions:
            entity.mentions.append(label)

    relations: list[Relation] = []
    for predicate, pattern, confidence in _RELATION_PATTERNS:
        for match in pattern.finditer(text):
            subject = _clean_entity(match.group("subject"))
            obj = _clean_entity(match.group("object"))
            if subject == obj or len(subject) < 2 or len(obj) < 2:
                continue
            for label in (subject, obj):
                ent_id = _entity_id(label)
                entities.setdefault(
                    ent_id,
                    Entity(
                        id=ent_id,
                        label=label,
                        type=_entity_type(label),
                        confidence=0.60,
                        mentions=[label],
                    ),
                )
            relations.append(
                Relation(
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    confidence=confidence,
                    evidence=match.group(0),
                    doc_id=doc_id,
                    lane="fast",
                )
            )

    return ExtractionResult(
        doc_id=doc_id,
        entities=sorted(entities.values(), key=lambda item: item.label.lower()),
        relations=relations,
        skipped=False,
        extractor="heuristic",
    )
