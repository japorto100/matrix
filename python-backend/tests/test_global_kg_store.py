from __future__ import annotations

from datetime import UTC, datetime

from memory_engine.global_kg import ClaimProposal, EntityRef, EvidenceRef
from memory_engine.global_kg_store import (
    InMemoryGlobalKGStore,
    PostgresGlobalKGStore,
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
    assert store.status()["count"] == 1


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
