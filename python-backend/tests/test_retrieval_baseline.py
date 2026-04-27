from __future__ import annotations

import pytest

from retrieval.api import retrieve
from retrieval.composers.context_bubble import build_context_bubble
from retrieval.core.types import RetrievalHit, RetrievalMode
from retrieval.evals.canaries import (
    GENERAL_VECTOR_CANARY,
    TRADING_GEO_KG_CANARY,
    evaluate_canary,
)
from retrieval.rerankers.rrf import reciprocal_rank_fusion
from retrieval.searchers.kg_claims import kg_claim_hits, kg_claim_rows_to_hits
from retrieval.searchers.vector_store import vector_search_hits
from retrieval.understanders.intent_router import route_intent
from retrieval.verifiers.citation import verify_context_support


def test_route_intent_prefers_graph_for_relation_queries() -> None:
    plan = route_intent("How is Russia connected to EU sanctions?")
    assert plan.mode is RetrievalMode.graph
    assert "graph_signal" in plan.reasons


def test_route_intent_temporal_graph_query() -> None:
    plan = route_intent("What changed today between China exports and copper?")
    assert plan.mode is RetrievalMode.temporal


def test_rrf_fuses_duplicate_hits_and_tracks_sources() -> None:
    vector = [RetrievalHit("a", "A vector", "vector"), RetrievalHit("b", "B", "vector")]
    kg = [RetrievalHit("a", "A graph", "kg"), RetrievalHit("c", "C", "kg")]

    fused = reciprocal_rank_fusion((vector, kg), limit=3)

    assert fused[0].id == "a"
    assert fused[0].source == "fused"
    assert fused[0].metadata["contributing_sources"] == ["kg", "vector"]


def test_context_bubble_keeps_references() -> None:
    bubble = build_context_bubble(
        [RetrievalHit("claim-1", "EU sanctions affect Russian oil flows.", "kg", 0.8)],
        token_budget=80,
    )

    assert "EU sanctions" in bubble.text
    assert bubble.references[0]["id"] == "claim-1"


@pytest.mark.asyncio
async def test_retrieve_hybrid_from_supplied_candidates() -> None:
    result = await retrieve(
        "How do EU sanctions affect Russian oil exports today?",
        vector_hits=[
            {
                "chunk_id": "chunk-1",
                "text": "Shipping notes mention Russian oil export pressure.",
                "score": 0.7,
                "source_uri": "doc://shipping",
            }
        ],
        kg_hits=[
            {
                "claim_id": "claim-1",
                "content": "EU SANCTIONED_BY Russia affects oil exports.",
                "score": 0.9,
                "metadata": {"path": ["EU", "SANCTIONED_BY", "Russia"]},
            }
        ],
    )

    assert result.intent == "temporal"
    assert result.degraded is False
    assert result.hits
    assert result.references
    assert "Russian oil" in result.context or "SANCTIONED_BY" in result.context


@pytest.mark.asyncio
async def test_retrieve_reports_degraded_missing_kg_hits() -> None:
    result = await retrieve(
        "How is Russia connected to EU sanctions?",
        vector_hits=[{"id": "v1", "text": "Only vector evidence."}],
    )

    assert result.intent == "graph"
    assert result.degraded is True
    assert result.degraded_reasons == ["NO_KG_HITS"]


def test_vector_search_adapter_normalizes_rows() -> None:
    class FakeStore:
        def search(self, query: str, n_results: int = 5) -> list[dict]:
            assert query == "oil sanctions"
            assert n_results == 2
            return [
                {
                    "id": "doc-1",
                    "text": "Oil sanctions context.",
                    "distance": 0.25,
                    "metadata": {"source_uri": "doc://oil"},
                }
            ]

    hits = vector_search_hits("oil sanctions", store=FakeStore(), limit=2)

    assert hits[0].id == "doc-1"
    assert hits[0].score == 0.75
    assert hits[0].source_uri == "doc://oil"


def test_kg_claim_adapter_normalizes_rows() -> None:
    hits = kg_claim_rows_to_hits(
        [
            {
                "claim_id": "claim-1",
                "claim_text": "EU SANCTIONED_BY Russia",
                "final_score": 0.91,
                "lane": "slow",
                "status": "promoted",
                "predicate": "SANCTIONED_BY",
                "path": ["EU", "SANCTIONED_BY", "Russia"],
                "source_refs": [{"source_layer": "world_evidence", "source_ref": "doc-1"}],
                "context_metadata": {"confidence": 0.91, "freshness_anchor": "2026-04-01"},
            }
        ]
    )

    assert hits[0].id == "claim-1"
    assert hits[0].source == "kg"
    assert hits[0].score == 0.91
    assert hits[0].metadata["path"] == ["EU", "SANCTIONED_BY", "Russia"]
    assert hits[0].metadata["source_refs"][0]["source_ref"] == "doc-1"
    assert hits[0].metadata["context_metadata"]["confidence"] == 0.91


@pytest.mark.asyncio
async def test_retrieve_can_pull_vector_store_when_requested() -> None:
    class FakeStore:
        def search(self, query: str, n_results: int = 5) -> list[dict]:
            return [{"id": "doc-1", "text": f"{query} from vector store", "score": 0.8}]

    result = await retrieve(
        "oil sanctions",
        use_vector_store=True,
        vector_store=FakeStore(),
        mode="text",
    )

    assert result.degraded is False
    assert result.hits and result.hits[0]["id"] == "doc-1"


@pytest.mark.asyncio
async def test_retrieve_can_pull_kg_store_when_requested() -> None:
    class FakeKGStore:
        def __init__(self) -> None:
            self.accessed: list[str] = []

        def search_claims(self, query: str, limit: int = 5) -> list[dict]:
            assert "sanctions" in query
            return [
                {
                    "claim_id": "claim-1",
                    "claim_text": "EU sanctions affect Russian oil exports.",
                    "confidence": 0.8,
                    "status": "promoted",
                }
            ]

        def record_claim_access(self, claim_ids: list[str]) -> int:
            self.accessed.extend(claim_ids)
            return len(claim_ids)

    store = FakeKGStore()
    result = await retrieve(
        "How is Russia connected to EU sanctions?",
        use_kg_store=True,
        kg_store=store,
    )

    assert result.degraded is False
    assert result.intent == "graph"
    assert result.hits and result.hits[0]["source"] == "kg"
    assert result.hits[0]["metadata"]["kg_access_recorded"] == 1
    assert store.accessed == ["claim-1"]


@pytest.mark.asyncio
async def test_retrieve_records_access_only_for_selected_kg_hits() -> None:
    class FakeKGStore:
        def __init__(self) -> None:
            self.accessed: list[str] = []

        def record_claim_access(self, claim_ids: list[str]) -> int:
            self.accessed.extend(claim_ids)
            return len(claim_ids)

    store = FakeKGStore()
    result = await retrieve(
        "How do EU sanctions affect Russian oil exports today?",
        kg_store=store,
        vector_hits=[{"id": "doc-1", "text": "Vector only", "score": 0.9}],
        kg_hits=[
            {"claim_id": "claim-1", "content": "Selected KG claim", "score": 0.8},
            {"claim_id": "claim-2", "content": "Truncated KG claim", "score": 0.7},
        ],
        max_hits=1,
    )

    assert result.hits and result.hits[0]["id"] == "doc-1"
    assert store.accessed == []


def test_kg_claim_hits_without_store_is_empty() -> None:
    assert kg_claim_hits("sanctions", store=None) == []


@pytest.mark.asyncio
async def test_retrieve_degrades_when_kg_store_fails() -> None:
    class FailingKGStore:
        def search_claims(self, query: str, limit: int = 5) -> list[dict]:
            raise RuntimeError("offline")

    result = await retrieve(
        "How is Russia connected to EU sanctions?",
        use_kg_store=True,
        kg_store=FailingKGStore(),
    )

    assert result.degraded is True
    assert "KG_SEARCH_FAILED" in (result.degraded_reasons or [])


def test_verify_context_support_flags_unsupported_claims() -> None:
    hits = [
        RetrievalHit(
            "claim-1",
            "EU sanctions affect Russian oil exports and shipping finance.",
            "kg",
        )
    ]

    result = verify_context_support(
        "EU sanctions affect Russian oil exports. Copper prices are guaranteed to rise.",
        hits,
    )

    assert result.supported is False
    assert result.cited_reference_ids == ("claim-1",)
    assert result.unsupported_claims == ("Copper prices are guaranteed to rise.",)


@pytest.mark.asyncio
async def test_trading_geo_canary_requires_vector_and_kg_sources() -> None:
    verdict = await evaluate_canary(TRADING_GEO_KG_CANARY)

    assert verdict["passed"] is True
    assert verdict["intent"] == "temporal"
    assert "kg" in verdict["sources"]
    assert "vector" in verdict["sources"]


@pytest.mark.asyncio
async def test_general_qa_canary_stays_vector_only() -> None:
    verdict = await evaluate_canary(GENERAL_VECTOR_CANARY)

    assert verdict["passed"] is True
    assert verdict["intent"] == "text"
    assert verdict["sources"] == ["vector"]
