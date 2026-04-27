---
title: Hybrid RAG Retrieval Live Verify
status: static_partial
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
---

# Live Verify

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
- Citation/support verification has a deterministic first pass that flags
  answer sentences not weakly supported by retrieved hits; LLM Self-RAG is not
  wired yet.
- Retrieval can optionally pull KG claim rows from a supplied global KG store
  adapter; this is unit-tested with a fake store and is not yet live-tested
  against Postgres/NornicDB.
- Retrieval reports `KG_SEARCH_FAILED`/`VECTOR_SEARCH_FAILED` as degraded
  reasons instead of raising through the agent path when an adapter is offline.
- OpenRouter embedding behavior is unit-tested with a mocked
  OpenAI-compatible `/embeddings` response; no live provider call has been made
  yet.
- KG extraction is unit-tested through the FastAPI app with the lightweight
  heuristic extractor; NornicDB/nonicdb projection is not live-verified yet.

## Live Stack

- Start ingestion worker with `EMBEDDER_PROVIDER=openrouter`.
- Verify a known OpenRouter/OpenAI-compatible embedding model returns vectors.
- Start `kg_pipeline` on port 8099 and verify `/health`.
- Ingest one note/link with `kg` sink enabled and verify KG candidates are
  returned by the worker.
- Run vector-only, KG-only and fused retrieval on the same query.
- Verify context assembly includes source refs and KG refs.
- Run Self-RAG/citation verification and inspect unsupported claims.
