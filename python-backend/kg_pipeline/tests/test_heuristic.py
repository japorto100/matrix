from __future__ import annotations

from fastapi.testclient import TestClient

from kg_pipeline.extractors.heuristic import extract_heuristic
from kg_pipeline.server import app


def test_extract_heuristic_finds_entities_and_relations() -> None:
    result = extract_heuristic(
        "EU sanctions Russia. China exports copper to Germany.",
        doc_id="doc-1",
    )

    labels = {entity.label for entity in result.entities}
    predicates = {relation.predicate for relation in result.relations}

    assert {"EU", "Russia", "China", "Germany"}.issubset(labels)
    assert "SANCTIONED_BY" in predicates
    assert "EXPORTS_TO" in predicates
    assert result.doc_id == "doc-1"
    assert not result.skipped


def test_extract_endpoint_returns_candidates() -> None:
    client = TestClient(app)

    response = client.post(
        "/extract",
        json={"text": "NATO affects Oil. Apple owns Beats.", "doc_id": "doc-2"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["extractor"] == "heuristic"
    assert body["skipped"] is False
    assert body["relations"]


def test_health_reports_lightweight_mode() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["projection_target"] == "nornicdb"


def test_propose_endpoint_returns_claim_proposals_without_persisting() -> None:
    client = TestClient(app)

    response = client.post(
        "/propose",
        json={
            "text": "EU sanctions Russia.",
            "doc_id": "doc-3",
            "source_uri": "doc://sanctions",
            "persist": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["proposal_count"] == 1
    assert body["proposals"][0]["predicate"] == "SANCTIONED_BY"
    assert body["persisted_claim_ids"] == []
    assert body["degraded"] is False
