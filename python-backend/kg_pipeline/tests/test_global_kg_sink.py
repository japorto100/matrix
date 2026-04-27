from __future__ import annotations

from datetime import UTC, datetime

from kg_pipeline.extractors.heuristic import extract_heuristic
from kg_pipeline.sinks.global_kg import proposals_from_extraction


def test_proposals_from_extraction_maps_relations_to_claims() -> None:
    result = extract_heuristic("EU sanctions Russia.", doc_id="doc-1")

    proposals = proposals_from_extraction(
        result,
        source_uri="doc://sanctions",
        valid_from=datetime(2026, 4, 27, tzinfo=UTC),
    )

    assert proposals
    proposal = proposals[0]
    assert proposal.subject.key == "russia"
    assert proposal.predicate == "SANCTIONED_BY"
    assert proposal.object_entity and proposal.object_entity.key == "eu"
    assert proposal.evidence[0].source_layer == "ingestion"
    assert proposal.evidence[0].source_ref == "doc-1"
    assert proposal.projection_payload()["predicate"] == "SANCTIONED_BY"
