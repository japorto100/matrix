"""Map KG extraction results to Feature 017 global KG claim proposals."""

from __future__ import annotations

from datetime import UTC, datetime

from kg_pipeline.core.types import ExtractionResult
from memory_engine.global_kg import ClaimProposal, EntityRef, EvidenceRef


def proposals_from_extraction(
    result: ExtractionResult,
    *,
    source_layer: str = "ingestion",
    source_uri: str | None = None,
    valid_from: datetime | None = None,
) -> list[ClaimProposal]:
    """Convert extracted relations into explicit KG claim proposals."""

    entity_by_id = {entity.id: entity for entity in result.entities}
    entity_by_label = {entity.label: entity for entity in result.entities}
    proposals: list[ClaimProposal] = []
    claim_valid_from = valid_from or datetime.now(UTC)

    for relation in result.relations:
        subject = entity_by_id.get(relation.subject) or entity_by_label.get(
            relation.subject
        )
        obj = entity_by_id.get(relation.object) or entity_by_label.get(relation.object)
        if subject is None or obj is None:
            continue
        evidence = EvidenceRef(
            source_layer=source_layer,
            source_ref=relation.doc_id or result.doc_id,
            source_uri=source_uri,
            quote=relation.evidence or None,
            metadata={
                "extractor": result.extractor,
                "subject_entity_id": relation.subject,
                "object_entity_id": relation.object,
            },
        )
        proposals.append(
            ClaimProposal(
                subject=EntityRef.from_name(subject.label, entity_type=subject.type),
                predicate=relation.predicate,
                object_entity=EntityRef.from_name(obj.label, entity_type=obj.type),
                valid_from=claim_valid_from,
                lane=relation.lane,
                status="proposed",
                confidence=relation.confidence,
                evidence=(evidence,),
                metadata={
                    "extractor": result.extractor,
                    "doc_id": result.doc_id,
                },
            )
        )
    return proposals
