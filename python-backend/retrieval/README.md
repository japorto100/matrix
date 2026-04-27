# Matrix Retrieval Pipeline (Venv 1, Phase 3)

**Status:** Feature 019 baseline active. Live search adapters are still pending,
but routing, RRF fusion and Context Bubble composition are implemented and
unit-tested.

## Purpose

End-to-end retrieval orchestration for the agent runtime:

```
query → understanders (intent, decompose, expand, hyde)
      → searchers     (bm25 + vector + kg + episodic, hybrid fusion)
      → rerankers     (cross-encoder, llm reranker, mmr)
      → verifiers     (self-rag, faithfulness)
      → composers     (context bubble, citation assembler)
```

Lives in the **main Venv 1** (no separate venv needed — sentence-transformers,
lancedb, chromadb have no dep conflicts with the agent runtime).

## Adoption sources (paperwatcher)

| Target | Source |
|---|---|
| `searchers/bm25_searcher.py` | `paperwatcher/core/chunk_bm25.py` |
| `searchers/vector_searcher.py` | wraps `memory_engine/vector_store.py` |
| `searchers/kg_searcher.py` | wraps `memory_engine/kg_store.py` (Kuzu) |
| `searchers/hindsight_searcher.py` | wraps `memory_engine/episodic_store.py` |
| `searchers/hybrid.py` | `paperwatcher/core/hybrid_retriever.py` |
| `rerankers/cross_encoder.py` | `paperwatcher/core/reranker.py` |
| `rerankers/llm_reranker.py` | `paperwatcher/core/llm_reranker.py` |
| `understanders/hyde.py` | `paperwatcher/core/hyde.py` |
| `understanders/intent_router.py` | `paperwatcher/core/intent_router.py` |
| `understanders/decomposer.py` | `paperwatcher/core/query_decomposer.py` |
| `understanders/expander.py` | `paperwatcher/core/query_expander.py` |
| `verifiers/self_rag.py` | `paperwatcher/core/self_rag.py` |
| `composers/context_bubble.py` | `paperwatcher/core/context_bubble.py` |
| `pipelines/hybrid_kg.py` | `paperwatcher/core/rag_pipeline.py` (adapted) |

## Decoupling rules (D17)

- May import `memory_engine.*` (shared data layer)
- MAY import `agent.llm_helper` and `agent.http_client` (helper modules used
  by reranker/hyde for LLM calls — these are pure utility, not agent runtime)
- MUST NOT import other agent modules (graph/, tools/, control/)

## Current Baseline

- `retrieval.api.retrieve()` accepts supplied `vector_hits` and `kg_hits`.
- `understanders.intent_router.route_intent()` selects text, graph, hybrid or
  temporal retrieval without LLM latency.
- `rerankers.rrf.reciprocal_rank_fusion()` merges vector/KG candidates with
  provenance metadata.
- `searchers.vector_store.vector_search_hits()` adapts the existing
  `memory_engine.VectorStore` facade into retrieval hits.
- `searchers.kg_claims.kg_claim_hits()` adapts Feature 017 global KG claim rows
  into retrieval hits when a Postgres/NornicDB store adapter is supplied.
- `composers.context_bubble.build_context_bubble()` creates compact,
  source-attributed prompt context.
- `verifiers.citation.verify_context_support()` provides a deterministic first
  pass for unsupported answer claims.
- `evals.canaries` provides fast canaries for two policy boundaries:
  trading/geopolitical multi-hop retrieval must use KG+vector evidence, while
  simple document QA must remain vector-only unless evals justify graph use.

## Activation (Live Adapters)

Next adapters should connect vector search, Feature 017 KG claim/path expansion
and citation verification behind the current contracts. NornicDB/nonicdb is the
first global KG projection target; FalkorDB is not the initial Matrix path.
