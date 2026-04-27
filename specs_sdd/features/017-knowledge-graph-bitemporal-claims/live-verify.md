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
- `memory_engine.global_kg_store` now exposes NornicDB projection-outbox read
  and replay snapshot APIs. Static tests verify replay snapshots preserve claim
  IDs, compact paths, evidence IDs and citation refs; DB-backed projection
  event roundtrip is covered when `GLOBAL_KG_DB_URL`, `MEMPALACE_DB_URL` or
  `HINDSIGHT_DB_URL` is present.
- `ClaimProposal.projection_payload()` now includes `evidence_refs` in addition
  to `evidence_ids`, so rebuildable projections can receive source URI,
  content hash and citation/chunk metadata without promoting raw tool output.
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
- `GlobalKGStore.record_claim_access(claim_ids)` now records access telemetry
  into `agent.kg_claim_access_stats`, not into the main claim row. In-memory
  smoke mode deduplicates a batch and counts existing claims only.
- Feature 019 retrieval now calls `record_claim_access` after Context Bubble
  selection, so only KG claims that reach answer-time context update access
  signals. Static retrieval tests verify skipped/truncated KG candidates are not
  counted.
- Postgres smoke with local `.env` credentials on 2026-04-27:
  `.venv/bin/python -m pytest tests/test_global_kg_store.py tests/test_global_kg.py -q`
  => `13 passed`; this verified access-stat UPSERT, duplicate claim ids counted
  once per batch, `last_accessed` is populated, and claim cleanup cascades.
- `kg_pipeline.sinks.global_kg` has unit tests for extraction-result to
  `ClaimProposal` mapping with evidence refs and NornicDB projection payloads.
- `kg_pipeline.sinks.global_kg` now refuses skipped extraction results and
  relations without both a source ref and evidence quote, preventing raw
  tool/output blobs from becoming global KG claims without provenance.
- `memory_engine.kg_validation` defines the Wisdom/GraphMERT validation
  contract: `TripleValidationInput`, `TripleValidationResult`, async validator
  protocol, explicit no-checkpoint GraphMERT placeholder, deterministic
  rule-based validator and `supports_slow_lane_promotion(...)`.
- `tests/test_kg_validation.py` verifies GraphMERT no-checkpoint skips,
  Fast-Lane validation is skipped rather than blocking fresh ingest, missing
  evidence is rejected, self-relations are hard negatives, and evidence-backed
  Slow-Lane triples can support but not force promotion.
- `retrieval.core.chunk_metadata.ChunkMetadata` defines the vector chunk
  metadata contract for fused retrieval: chunk id, source URI, embedding
  model/version/dimension, ingest timestamp, TTL, validity window and entity
  signatures. `vector_search_hits(...)` normalizes rows through this contract.
- Feature 019 canary aggregation now reports pass rate, Recall@k and nDCG@k
  over small hybrid retrieval canaries. This is the first static slice of the
  RAGSearch-style matched-budget comparison; answer faithfulness and latency
  remain larger follow-up metrics.
- KG pipeline `/propose` is unit-tested in non-persist mode. Persist mode is
  guarded and reports degraded state if the global KG store is unavailable.
- Meta-Harness Feature 016 now includes
  `data/harness/global_kg_boundaries/scenarios.json`, which statically verifies
  the global KG/nonicdb boundary against personal memory routes and silent KG
  promotion.
- `GlobalKGStore.correct_claim(...)` now implements append-only bitemporal
  correction semantics without lossy valid-period truncation: current
  overlapping claims for the same conflict key are system-time closed
  (`sys_to=now()`), marked `superseded`, and the corrected claim is inserted as
  the only current version.
- `GlobalKGStore.list_claim_versions(conflict_key)` exposes historical and
  current versions for audit/review. Unit and Postgres smoke tests verify that
  superseded claims remain visible in version history but are excluded from
  current `search_claims(...)` retrieval.
- Postgres correction smoke with local `.env` credentials on 2026-04-27:
  `HINDSIGHT_DB_URL=... .venv/bin/alembic upgrade head && .venv/bin/python -m pytest tests/test_global_kg_store.py tests/test_kg_claim_migration_static.py -q`
  => `12 passed`; this verified correction history, current-truth filtering,
  pgvector claim retrieval, schema constraints and cleanup.

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
