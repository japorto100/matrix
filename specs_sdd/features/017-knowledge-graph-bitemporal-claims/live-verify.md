---
title: Knowledge Graph Live Verify
status: static_partial
owner: filip
created: 2026-04-26
updated: 2026-04-27
feature_id: 017
---

# Live Verify

## Static Verify

- `python-backend/.venv/bin/python -m pytest kg_pipeline/tests/test_heuristic.py -q`
  passed on 2026-04-27.
- `python-backend/.venv/bin/python -m ruff check ...` passed for the touched
  KG pipeline files on 2026-04-27.
- `/health` now reports the lightweight extractor and NornicDB/nonicdb as the
  projection target.
- `/extract` returns entities and relation candidates from a deterministic
  heuristic extractor for smoke-level KG candidate generation.
- Alembic migration `030_global_kg_bitemporal_claims` is statically tested for
  revision chain, bitemporal fields, evidence table, conflict exclusion and
  NornicDB projection outbox.
- `memory_engine.global_kg` has unit tests for canonical keys, claim IDs,
  conflict keys, decay scoring and NornicDB projection payloads.
- `memory_engine.global_kg_store` has unit tests for in-memory claim roundtrip,
  mock-store factory and Postgres unavailable status without DSN.
- `memory_engine.global_kg_store` now supports claim embeddings stored from
  `ClaimProposal.metadata.embedding` and pgvector KNN candidate retrieval via
  `search_claims(..., query_embedding=..., embedding_model=...)`, with lexical
  fallback when no vector candidates exist.
- KG claim rows now expose answer-time context metadata for Feature 019:
  compact `[subject, predicate, object]` paths, subject/object identity,
  evidence/source refs, status, lane, confidence, valid period and freshness
  anchor.
- `GlobalKGStore.expand_claim_context(claim_id)` is implemented for the
  in-memory and Postgres stores so fused retrieval can expand a selected KG
  claim without loading a large graph neighborhood.
- Postgres smoke on 2026-04-27:
  `.venv/bin/python -m pytest tests/test_global_kg_store.py tests/test_retrieval_baseline.py -q`
  with `GLOBAL_KG_DB_URL` exported from local `.env` credentials => `22
  passed`; this inserted a synthetic 3D test claim, retrieved it through
  pgvector despite no lexical overlap, verified compact KG path/source-ref
  output plus `expand_claim_context`, and cleaned up the claim row.
- `kg_pipeline.sinks.global_kg` has unit tests for extraction-result to
  `ClaimProposal` mapping with evidence refs and NornicDB projection payloads.
- KG pipeline `/propose` is unit-tested in non-persist mode. Persist mode is
  guarded and reports degraded state if the global KG store is unavailable.

## Live Stack

- Start Matrix Postgres and Python backend.
- Insert or ingest one evidence item.
- Extract one candidate KG claim with evidence refs.
- Promote the claim.
- Query current truth and historical truth.
- Add a correction and verify the older version remains historical only.
- Run KG retrieval with semantic + temporal/access decay.
- Run vector-only, KG-only and fused retrieval on the same query.
- Verify RRF output includes chunk refs and KG claim/entity refs.
- Verify graph context is limited to short explanatory paths.
- Inspect the claim and provenance through `/memory/kg` or successor Control UI.
