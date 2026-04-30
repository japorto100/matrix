from __future__ import annotations

import pytest

from retrieval.api import retrieve
from retrieval.composers.context_bubble import build_context_bubble
from retrieval.core.types import RetrievalHit, RetrievalMode
from retrieval.evals.canaries import (
    GENERAL_VECTOR_CANARY,
    SOURCE_PROVENANCE_CANARY,
    TRADING_GEO_KG_CANARY,
    CanaryExpectation,
    RetrievalCanary,
    evaluate_canary,
    evaluate_canary_set,
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


def test_context_bubble_applies_structural_priors_and_diversity_gate() -> None:
    bubble = build_context_bubble(
        [
            RetrievalHit(
                "refs-1",
                "Low value bibliography entry about copper and sanctions.",
                "vector",
                0.81,
                metadata={"section": "references", "embedding": [1.0, 0.0]},
            ),
            RetrievalHit(
                "claim-1",
                "Promoted KG claim: sanctions affect Russian oil shipping finance.",
                "kg",
                0.80,
                metadata={
                    "status": "promoted",
                    "confidence": 0.9,
                    "embedding": [0.0, 1.0],
                },
            ),
            RetrievalHit(
                "claim-dup",
                "Promoted KG claim: sanctions affect Russian oil shipping finance.",
                "kg",
                0.79,
                metadata={"status": "promoted", "embedding": [0.0, 1.0]},
            ),
        ],
        token_budget=120,
        max_hits=3,
    )

    assert [hit.id for hit in bubble.hits] == ["claim-1", "refs-1"]
    assert bubble.references[0]["metadata"]["context_bubble"]["structural_prior"] > 1.0


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
    assert result.hits[0]["metadata"]["provenance_status"] == "complete"
    assert result.references[0]["metadata"]["provenance_status"] == "complete"
    assert result.runtime_events
    assert [event["name"] for event in result.runtime_events[:2]] == [
        "rag.retrieve.started",
        "rag.retrieve.completed",
    ]
    completed = result.runtime_events[1]
    assert completed["metadata"]["selected_context_ids"]
    assert completed["metadata"]["selected_kg_claim_ids"] == ["claim-1"]
    assert "Russian oil" not in str(completed["metadata"])
    assert result.runtime_events[2]["kind"] == "kg"


@pytest.mark.asyncio
async def test_retrieve_audits_runtime_events_when_scoped(monkeypatch) -> None:
    from agent.audit.logger import AuditAction
    from retrieval import api as retrieval_api

    audit_rows: list[dict] = []

    async def _capture_audit(**kwargs):
        audit_rows.append(kwargs)

    monkeypatch.setattr(retrieval_api, "audit_log", _capture_audit)

    await retrieve(
        "How do EU sanctions affect Russian oil exports today?",
        thread_id="thread-rag",
        user_id="u1",
        audit_runtime_events=True,
        vector_hits=[
            {
                "chunk_id": "chunk-1",
                "text": "Shipping notes mention Russian oil export pressure.",
                "score": 0.7,
                "source_uri": "doc://shipping",
            }
        ],
    )

    assert audit_rows
    row = audit_rows[0]
    assert row["action"] == AuditAction.RAG_RETRIEVAL
    assert row["thread_id"] == "thread-rag"
    assert row["metadata"]["runtime_events"][0]["name"] == "rag.retrieve.started"
    assert "query_digest" in row["metadata"]
    assert "Russian oil" not in str(row["metadata"])


@pytest.mark.asyncio
async def test_retrieve_can_fail_closed_on_missing_context_provenance() -> None:
    result = await retrieve(
        "What does the source say?",
        mode="text",
        require_context_provenance=True,
        vector_hits=[
            {
                "id": "chunk-without-source",
                "text": "Unattributed context.",
                "score": 0.9,
            }
        ],
    )

    assert result.degraded is True
    assert "CONTEXT_PROVENANCE_MISSING" in (result.degraded_reasons or [])
    assert result.hits and result.hits[0]["metadata"]["provenance_status"] == "missing"
    assert result.runtime_events
    assert result.runtime_events[1]["metadata"]["missing_provenance_ids"] == [
        "chunk-without-source"
    ]


@pytest.mark.asyncio
async def test_retrieve_blocks_lexical_answer_support_without_provenance() -> None:
    result = await retrieve(
        "Find unattributed lexical evidence",
        mode="text",
        require_context_provenance=True,
        bm25_hits=[
            {
                "id": "bm25-unattributed",
                "text": "A lexical match without source cannot support an answer.",
                "score": 3.1,
            }
        ],
    )

    assert result.degraded is True
    assert "CONTEXT_PROVENANCE_MISSING" in (result.degraded_reasons or [])
    assert result.hits and result.hits[0]["metadata"]["retrieval_lane"] == "bm25"
    assert result.hits[0]["metadata"]["provenance_status"] == "missing"
    completed = result.runtime_events[1]["metadata"]
    assert completed["lexical_hit_count"] == 1
    assert completed["missing_provenance_ids"] == ["bm25-unattributed"]


@pytest.mark.asyncio
async def test_retrieve_preserves_bm25_and_regex_lane_metadata() -> None:
    result = await retrieve(
        "Find tool retry guard evidence",
        mode="text",
        bm25_hits=[
            {
                "id": "bm25-tool-guard",
                "text": "Tool retry guard stops repeated tool failures.",
                "score": 2.4,
                "source_uri": "doc://agent-runtime",
                "metadata": {"citation_ref": "doc://agent-runtime#bm25"},
            }
        ],
        regex_hits=[
            {
                "id": "regex-tool-guard",
                "text": "AGENT_MAX_TOOL_FAILURES_PER_TOOL is configured.",
                "score": 1.8,
                "source_uri": "doc://agent-config",
                "metadata": {"citation_ref": "doc://agent-config#regex"},
            }
        ],
    )

    assert result.degraded is False
    assert result.hits
    lanes = {hit["metadata"]["retrieval_lane"] for hit in result.hits}
    assert lanes <= {"bm25", "regex", "fused"}
    assert {"bm25", "regex"} & lanes
    completed = result.runtime_events[1]
    assert completed["metadata"]["lexical_hit_count"] == 2
    assert completed["metadata"]["lane_counts"] == {"bm25": 1, "regex": 1}
    assert "Tool retry guard" not in str(completed["metadata"])


@pytest.mark.asyncio
async def test_retrieve_returns_metadata_only_source_candidates() -> None:
    result = await retrieve(
        "Find source candidates for a report",
        mode="text",
        source_candidates=[
            {
                "id": "source-report-1",
                "title": "Quarterly report",
                "source": "kb",
                "source_uri": "doc://quarterly-report",
                "metadata": {
                    "source_artifact_id": "artifact-report-1",
                    "chunk_hash": "sha256:report",
                },
                "content": "This full source body must not appear in candidates.",
            }
        ],
        vector_hits=[
            {
                "id": "chunk-report-1",
                "text": "Quarterly report says revenue increased.",
                "score": 0.9,
                "source_uri": "doc://quarterly-report",
                "metadata": {
                    "source_artifact_id": "artifact-report-1",
                    "chunk_id": "chunk-report-1",
                    "citation_ref": "doc://quarterly-report#chunk-report-1",
                },
            }
        ],
    )

    assert result.source_candidates
    candidate = result.source_candidates[0]
    assert candidate["id"] == "source-report-1"
    assert candidate["title"] == "Quarterly report"
    assert candidate["source_uri"] == "doc://quarterly-report"
    assert candidate["metadata"]["source_artifact_id"] == "artifact-report-1"
    assert "content" not in candidate
    assert "full source body" not in str(result.source_candidates)
    completed = result.runtime_events[1]["metadata"]
    assert completed["source_candidate_count"] >= 1
    assert "source-report-1" in completed["source_candidate_ids"]


@pytest.mark.asyncio
async def test_retrieve_applies_semantic_filter_to_supplied_candidates() -> None:
    result = await retrieve(
        "What is the agent tool success rate?",
        mode="text",
        semantic_filter={
            "semantic_term_ids": ("agent_tool_success_rate",),
            "metric_id": "agent_tool_success_rate",
        },
        vector_hits=[
            {
                "id": "chunk-unrelated",
                "text": "Generic agent audit prose.",
                "score": 0.95,
                "metadata": {"semantic_term_ids": ["tool_execution"]},
            },
            {
                "id": "chunk-tool-success",
                "text": "Agent tool success rate is successful_tool_results / total_tool_results.",
                "score": 0.7,
                "metadata": {
                    "semantic_term_ids": [
                        "agent_tool_success_rate",
                        "tool_execution",
                    ],
                    "metric_id": "agent_tool_success_rate",
                    "semantic_catalog_version": "1.0.0",
                },
            },
        ],
    )

    assert result.degraded is False
    assert result.hits and [hit["id"] for hit in result.hits] == ["chunk-tool-success"]
    assert result.hits[0]["metadata"]["semantic_filter"]["metric_id"] == (
        "agent_tool_success_rate"
    )


@pytest.mark.asyncio
async def test_retrieve_degrades_when_semantic_filter_has_no_match() -> None:
    result = await retrieve(
        "What is the agent tool success rate?",
        mode="text",
        semantic_filter={"semantic_term_ids": ("agent_tool_success_rate",)},
        vector_hits=[
            {
                "id": "chunk-unrelated",
                "text": "Generic agent audit prose.",
                "score": 0.95,
                "metadata": {"semantic_term_ids": ["tool_execution"]},
            },
        ],
    )

    assert result.degraded is True
    assert "SEMANTIC_FILTER_NO_MATCH" in (result.degraded_reasons or [])
    assert result.hits == []


@pytest.mark.asyncio
async def test_retrieve_builds_semantic_filter_from_phrase() -> None:
    result = await retrieve(
        "Find retrieval quality evidence.",
        mode="text",
        semantic_phrase="retrieval quality",
        vector_hits=[
            {
                "id": "chunk-retrieval-quality",
                "text": "Retrieval pass rate is a run-scoped benchmark metric.",
                "score": 0.8,
                "metadata": {"metric_id": "retrieval_pass_rate"},
            }
        ],
    )

    assert result.degraded is False
    assert result.hits and result.hits[0]["id"] == "chunk-retrieval-quality"
    assert result.hits[0]["metadata"]["semantic_filter"]["metric_id"] == (
        "retrieval_pass_rate"
    )


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
                    "metadata": {
                        "source_uri": "doc://oil",
                        "embedding_version": "bge-small@2026-04",
                        "embedding_dimension": "384",
                        "timestamp_ingested": "2026-04-27T00:00:00Z",
                        "ttl_seconds": 86400,
                        "entity_signatures": ["eu", "russia"],
                    },
                }
            ]

    hits = vector_search_hits("oil sanctions", store=FakeStore(), limit=2)

    assert hits[0].id == "doc-1"
    assert hits[0].score == 0.75
    assert hits[0].source_uri == "doc://oil"
    assert hits[0].metadata["chunk_id"] == "doc-1"
    assert hits[0].metadata["embedding_version"] == "bge-small@2026-04"
    assert hits[0].metadata["embedding_dimension"] == 384
    assert hits[0].metadata["ingested_at"] == "2026-04-27T00:00:00Z"
    assert hits[0].metadata["ttl_seconds"] == 86400
    assert hits[0].metadata["entity_signatures"] == ["eu", "russia"]


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


def test_verify_context_support_can_require_explicit_citations() -> None:
    hits = [
        RetrievalHit(
            "claim-1",
            "EU sanctions affect Russian oil exports and shipping finance.",
            "kg",
        )
    ]

    missing = verify_context_support(
        "EU sanctions affect Russian oil exports.",
        hits,
        require_citations=True,
    )
    cited = verify_context_support(
        "EU sanctions affect Russian oil exports [claim-1].",
        hits,
        require_citations=True,
    )

    assert missing.supported is False
    assert missing.missing_citation_claims == ("EU sanctions affect Russian oil exports.",)
    assert cited.supported is True
    assert cited.citation_ratio == 1.0


@pytest.mark.asyncio
async def test_retrieve_can_verify_generated_answer_citations() -> None:
    result = await retrieve(
        "How do EU sanctions affect Russian oil exports?",
        mode="graph",
        kg_hits=[
            {
                "claim_id": "claim-1",
                "content": "EU sanctions affect Russian oil exports and shipping finance.",
                "score": 0.9,
            }
        ],
        answer="EU sanctions affect Russian oil exports [claim-1].",
        require_citations=True,
    )

    assert result.verification is not None
    assert result.verification["supported"] is True
    assert result.verification["cited_reference_ids"] == ["claim-1"]


@pytest.mark.asyncio
async def test_trading_geo_canary_requires_vector_and_kg_sources() -> None:
    verdict = await evaluate_canary(TRADING_GEO_KG_CANARY)

    assert verdict["passed"] is True
    assert verdict["intent"] == "temporal"
    assert "kg" in verdict["sources"]
    assert "vector" in verdict["sources"]
    assert ["EU", "SANCTIONS", "Russian oil", "SHIPPING_INSURANCE"] in verdict[
        "kg_paths"
    ]


@pytest.mark.asyncio
async def test_general_qa_canary_stays_vector_only() -> None:
    verdict = await evaluate_canary(GENERAL_VECTOR_CANARY)

    assert verdict["passed"] is True
    assert verdict["intent"] == "text"
    assert verdict["sources"] == ["vector"]


@pytest.mark.asyncio
async def test_canary_can_require_generated_answer_citations() -> None:
    canary = RetrievalCanary(
        id="citation-complete-001",
        query="How do EU sanctions affect Russian oil exports?",
        expectation=CanaryExpectation(
            intent="graph",
            required_sources=("kg",),
            required_reference_ids=("claim-1",),
            required_cited_reference_ids=("claim-1",),
            generated_answer="EU sanctions affect Russian oil exports [claim-1].",
            require_citations=True,
        ),
        kg_hits=(
            {
                "claim_id": "claim-1",
                "content": "EU sanctions affect Russian oil exports and shipping finance.",
                "score": 0.9,
            },
        ),
        mode="graph",
    )

    verdict = await evaluate_canary(canary)

    assert verdict["passed"] is True
    assert verdict["verification"]["supported"] is True
    assert verdict["cited_reference_ids"] == ["claim-1"]


@pytest.mark.asyncio
async def test_source_provenance_canary_requires_chunk_citation_metadata() -> None:
    verdict = await evaluate_canary(SOURCE_PROVENANCE_CANARY)

    assert verdict["passed"] is True
    assert verdict["intent"] == "text"
    assert verdict["sources"] == ["vector"]
    assert verdict["cited_reference_ids"] == ["chunk-source-provenance"]
    assert verdict["ranked_reference_ids"] == ["chunk-source-provenance"]
    metadata = verdict["reference_metadata"]["chunk-source-provenance"]
    assert metadata["source_artifact_id"] == "artifact-researchwatcher-provenance"
    assert metadata["citation_ref"].endswith("#chunk=chunk-source-provenance")
    assert metadata["parser_name"] == "markdown"


@pytest.mark.asyncio
async def test_canary_set_reports_recall_and_ndcg() -> None:
    report = await evaluate_canary_set(
        [TRADING_GEO_KG_CANARY, GENERAL_VECTOR_CANARY, SOURCE_PROVENANCE_CANARY],
        k=5,
    )

    assert report["count"] == 3
    assert report["pass_rate"] == 1.0
    assert report["recall@5"] == 1.0
    assert report["ndcg@5"] >= 0.8
