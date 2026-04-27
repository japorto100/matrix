from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest

from memory_engine.global_kg import ClaimProposal, EntityRef, EvidenceRef
from memory_engine.global_kg_store import (
    InMemoryGlobalKGStore,
    PostgresGlobalKGStore,
    _claim_embedding,
    _vector_literal,
    create_global_kg_store,
)


def _proposal() -> ClaimProposal:
    return ClaimProposal(
        subject=EntityRef.from_name("European Union", entity_type="institution"),
        predicate="SANCTIONED_BY",
        object_entity=EntityRef.from_name("Russia", entity_type="country"),
        valid_from=datetime(2026, 4, 1, tzinfo=UTC),
        confidence=0.8,
        evidence=(EvidenceRef(source_layer="world_evidence", source_ref="doc-1"),),
    )


def test_in_memory_global_kg_store_roundtrip() -> None:
    store = InMemoryGlobalKGStore()
    claim_id = store.propose_claim(_proposal())

    rows = store.search_claims("Russia sanctions", limit=5)

    assert rows[0]["claim_id"] == claim_id
    assert rows[0]["predicate"] == "SANCTIONED_BY"
    assert rows[0]["final_score"] > 0
    assert rows[0]["path"] == ["European Union", "SANCTIONED_BY", "Russia"]
    assert rows[0]["source_refs"][0]["source_ref"] == "doc-1"
    assert store.status()["count"] == 1


def test_in_memory_global_kg_expands_claim_context() -> None:
    store = InMemoryGlobalKGStore()
    claim_id = store.propose_claim(_proposal())

    context = store.expand_claim_context(claim_id)

    assert context is not None
    assert context["claim_id"] == claim_id
    assert context["path"] == ["European Union", "SANCTIONED_BY", "Russia"]
    assert context["subject"]["canonical_key"] == "european:union"
    assert context["object"]["canonical_key"] == "russia"
    assert context["context_metadata"]["status"] == "proposed"
    assert context["context_metadata"]["confidence"] == 0.8
    assert context["source_refs"][0]["source_ref"] == "doc-1"


def test_create_global_kg_store_mock(monkeypatch) -> None:
    monkeypatch.setenv("GLOBAL_KG_MOCK", "true")

    store = create_global_kg_store()

    assert isinstance(store, InMemoryGlobalKGStore)


def test_postgres_global_kg_status_unavailable_without_dsn(monkeypatch) -> None:
    monkeypatch.delenv("GLOBAL_KG_DB_URL", raising=False)
    monkeypatch.delenv("HINDSIGHT_DB_URL", raising=False)
    store = PostgresGlobalKGStore()

    status = store.status()

    assert status["status"] == "unavailable"
    assert status["provider"] == "postgres"


def test_claim_embedding_metadata_to_pgvector_literal() -> None:
    literal, dim, model = _claim_embedding(
        {
            "embedding": [0.125, -1, 2.5],
            "embedding_model": "test-3d",
        }
    )

    assert literal == "[0.125,-1,2.5]"
    assert dim == 3
    assert model == "test-3d"


def test_vector_literal_rejects_nan() -> None:
    with pytest.raises(ValueError):
        _vector_literal([float("nan")])


def test_postgres_global_kg_vector_search_roundtrip() -> None:
    db_url = (
        os.environ.get("GLOBAL_KG_DB_URL")
        or os.environ.get("MEMPALACE_DB_URL")
        or os.environ.get("HINDSIGHT_DB_URL")
    )
    if not db_url:
        pytest.skip("requires GLOBAL_KG_DB_URL, MEMPALACE_DB_URL or HINDSIGHT_DB_URL")

    suffix = uuid.uuid4().hex
    proposal = ClaimProposal(
        subject=EntityRef.from_name(f"Vector Test Subject {suffix}", entity_type="test"),
        predicate="AFFECTS",
        object_entity=EntityRef.from_name(f"Vector Test Object {suffix}", entity_type="test"),
        valid_from=datetime(2026, 4, 1, tzinfo=UTC),
        confidence=0.42,
        evidence=(EvidenceRef(source_layer="manual", source_ref=f"vector-test-{suffix}"),),
        metadata={"embedding": [1.0, 0.0, 0.0], "embedding_model": "test-3d"},
    )
    store = PostgresGlobalKGStore(db_url)
    claim_id = store.propose_claim(proposal)

    try:
        rows = store.search_claims(
            "lexically unrelated query",
            query_embedding=[1.0, 0.0, 0.0],
            embedding_model="test-3d",
            limit=3,
        )
        assert rows
        assert rows[0]["claim_id"] == claim_id
        assert rows[0]["path"] == [
            f"Vector Test Subject {suffix}",
            "AFFECTS",
            f"Vector Test Object {suffix}",
        ]
        assert rows[0]["source_refs"][0]["source_ref"] == f"vector-test-{suffix}"
        assert rows[0]["semantic_similarity"] == pytest.approx(1.0)
        assert rows[0]["final_score"] > 0.9

        context = store.expand_claim_context(claim_id)
        assert context is not None
        assert context["path"] == rows[0]["path"]
        assert context["context_metadata"]["lane"] == "fast"
    finally:
        with store._connect() as conn:  # noqa: SLF001 - cleanup for live DB smoke
            with conn.cursor() as cur:
                cur.execute("DELETE FROM agent.kg_claims WHERE claim_id = %s", (claim_id,))
