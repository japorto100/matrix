# Matrix Retrieval Pipeline (Venv 1, Phase 3)

**Status:** Skeleton (Phase 3 not yet implemented). See exec-15 §5.8 + plan file.

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

## Activation (Phase 3)

Will happen after Slice 2 backend (ingestion) is verified end-to-end and
Slice 3 backend (memory.py + episodes.py) is built. At that point we have
real data in Hindsight + Kuzu and can start composing actual retrieval pipelines.
