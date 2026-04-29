---
title: Hybrid RAG Retrieval Live Verify
status: static_partial
owner: filip
created: 2026-04-27
updated: 2026-04-30
feature_id: 019
---

# Live Verify

## 2026-04-29 Browser/Semantic/Visual Follow-Up

- Compare Feature 026 browser-local retrieval with backend retrieval on one
  canary set.
- Verify Feature 025 semantic filters affect retrieval deterministically.
- Verify Feature 028 visual-layout blocks appear with coordinate refs in
  retrieved context.
- Static prerequisite passed on 2026-04-30:
  `uv run python -m meta_harness.meta_cli knowledge-contract --run-id run-knowledge-contract-static --data-dir /tmp/matrix-knowledge-contract`
  passed 5/5 provider-free Memory/KG/RAG/Semantic boundary scenarios.

## Static Verify

- `python-backend/.venv/bin/python -m pytest ingestion/tests/test_embedders.py kg_pipeline/tests/test_heuristic.py -q`
  passed on 2026-04-27.
- `python-backend/.venv/bin/python -m pytest tests/test_retrieval_baseline.py
  ingestion/tests/test_embedders.py kg_pipeline/tests/test_heuristic.py -q`
  passed on 2026-04-27.
- `python-backend/.venv/bin/python -m ruff check ...` passed for the touched
  ingestion embedder and KG pipeline files on 2026-04-27.
- Retrieval intent routing, RRF fusion, source references and Context Bubble
  assembly are unit-tested with supplied vector/KG candidates.
- Retrieval can optionally pull from the existing Matrix
  `memory_engine.VectorStore` facade; this adapter is unit-tested with a fake
  store and has not yet been live-tested against Chroma/pgvector.
- `memory_engine.VectorStore.add(...)` now enriches chunk metadata with
  `embedding_model`, `embedding_version` and `embedding_dimension` while
  preserving explicit provider metadata. Mock VectorStore tests cover default
  metadata and custom OpenRouter/remote-provider-compatible overrides.
- Vector search hits normalize Feature-017 chunk metadata via
  `ChunkMetadata`: source URI, embedding version/dimension, ingest timestamp,
  TTL and entity signatures are carried into `RetrievalHit.metadata`.
- Citation/support verification has a deterministic first pass that flags
  answer sentences not weakly supported by retrieved hits; it can now require
  explicit `[reference-id]`/`[context-index]` citations and can be invoked from
  `retrieve(..., answer=..., require_citations=True)` so generated-answer
  verification degrades retrieval results when unsupported or uncited claims
  appear. LLM Self-RAG remains a later optional verifier.
- Context Bubble selection now applies lightweight structural priors from
  section/status/confidence metadata and rejects near-duplicate candidates via
  embedding cosine or text-token overlap before consuming prompt budget. The
  behavior is covered by `tests/test_retrieval_baseline.py`.
- Retrieval can optionally pull KG claim rows from a supplied global KG store
  adapter; this is unit-tested with a fake store and is not yet live-tested
  against Postgres/NornicDB.
- The Postgres global-KG adapter is now live-smoked against pgvector: a
  synthetic claim with a 3D embedding is stored from `ClaimProposal.metadata`,
  retrieved with `search_claims(..., query_embedding=...)` despite no lexical
  overlap, and returned with `semantic_similarity`, decay-adjusted
  `final_score`, provenance and metadata.
- KG hits now carry Feature-017 context metadata through the Feature-019
  adapter: compact graph path, source refs, subject/object ids and lane/status/
  confidence metadata. This is unit-tested and live-smoked through Postgres via
  the global-KG store tests.
- Retrieval records Feature-017 KG access telemetry after Context Bubble
  selection when the KG store exposes `record_claim_access`. Unit tests verify
  selected KG hits are counted and KG candidates dropped by `max_hits` are not
  counted.
- Added deterministic canaries for the two immediate eval boundaries:
  `trading-geo-kg-001` requires fused vector+KG evidence, while
  `general-vector-001` verifies simple document QA stays vector-only.
  Covered by `tests/test_retrieval_baseline.py`.
- Canary sets now aggregate pass rate, Recall@k and nDCG@k via
  `evaluate_canary_set(...)`, giving a small RAGSearch-style regression gate
  before larger benchmark integrations.
- Retrieval reports `KG_SEARCH_FAILED`/`VECTOR_SEARCH_FAILED` as degraded
  reasons instead of raising through the agent path when an adapter is offline.
- OpenRouter embedding behavior is unit-tested with a mocked
  OpenAI-compatible `/embeddings` response; no live provider call has been made
  yet.
- KG extraction is unit-tested through the FastAPI app with the lightweight
  heuristic extractor; NornicDB/nonicdb projection is not live-verified yet.
- `cd python-backend && .venv/bin/python -m pytest tests/test_retrieval_baseline.py -q`
  passed on 2026-04-27 (`20 passed`), covering Context Bubble structural
  priors/diversity, RRF, KG access telemetry, canaries and citation
  verification.
- `cd python-backend && .venv/bin/ruff check retrieval/api.py
  retrieval/composers/context_bubble.py retrieval/verifiers/citation.py
  tests/test_retrieval_baseline.py` passed on 2026-04-27.

## Live Stack

- Start ingestion worker with `EMBEDDER_PROVIDER=openrouter`.
- Verify a known OpenRouter/OpenAI-compatible embedding model returns vectors.
- Start `kg_pipeline` on port 8099 and verify `/health`.
- Ingest one note/link with `kg` sink enabled and verify KG candidates are
  returned by the worker.
- Run vector-only, KG-only and fused retrieval on the same query.
- Verify context assembly includes source refs and KG refs.
- Run Self-RAG/citation verification and inspect unsupported claims.
