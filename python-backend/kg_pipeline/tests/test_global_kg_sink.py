from __future__ import annotations

from datetime import UTC, datetime

from kg_pipeline.core.types import Entity, ExtractionResult, Relation
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


def test_proposals_from_extraction_preserves_source_artifact_citation_metadata() -> None:
    result = extract_heuristic("EU sanctions Russia.", doc_id="chunk-1")

    proposals = proposals_from_extraction(
        result,
        source_uri="doc://fallback",
        evidence_metadata_by_ref={
            "chunk-1": {
                "source_artifact_id": "artifact-1",
                "source_uri": "file:///papers/sanctions.md",
                "chunk_id": "chunk-1",
                "chunk_index": 0,
                "chunk_hash": "hash-1",
                "citation_ref": "file:///papers/sanctions.md#chunk=chunk-1&page=4",
                "page_start": 4,
                "parser_name": "markdown",
                "parser_version": "1",
                "chunker_name": "token",
            }
        },
    )

    evidence = proposals[0].evidence[0]
    assert evidence.source_uri == "file:///papers/sanctions.md"
    assert evidence.metadata["source_artifact_id"] == "artifact-1"
    assert evidence.metadata["citation_ref"].endswith("#chunk=chunk-1&page=4")
    assert evidence.metadata["chunker_name"] == "token"


def test_proposals_from_extraction_skip_skipped_results() -> None:
    result = ExtractionResult(
        doc_id="doc-1",
        entities=[
            Entity(id="e1", label="EU", type="organization"),
            Entity(id="e2", label="Russia", type="country"),
        ],
        relations=[
            Relation(
                subject="e2",
                predicate="SANCTIONED_BY",
                object="e1",
                evidence="EU sanctions Russia.",
                doc_id="doc-1",
            )
        ],
        skipped=True,
    )

    assert proposals_from_extraction(result) == []


def test_proposals_from_extraction_requires_source_ref() -> None:
    result = ExtractionResult(
        entities=[
            Entity(id="e1", label="EU", type="organization"),
            Entity(id="e2", label="Russia", type="country"),
        ],
        relations=[
            Relation(
                subject="e2",
                predicate="SANCTIONED_BY",
                object="e1",
                evidence="EU sanctions Russia.",
            )
        ],
    )

    assert proposals_from_extraction(result) == []


def test_proposals_from_extraction_requires_evidence_quote() -> None:
    result = ExtractionResult(
        doc_id="doc-1",
        entities=[
            Entity(id="e1", label="EU", type="organization"),
            Entity(id="e2", label="Russia", type="country"),
        ],
        relations=[
            Relation(
                subject="e2",
                predicate="SANCTIONED_BY",
                object="e1",
                evidence=" ",
                doc_id="doc-1",
            )
        ],
    )

    assert proposals_from_extraction(result) == []
