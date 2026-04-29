---
title: Knowledge Graph Closeout
status: open
owner: filip
created: 2026-04-26
updated: 2026-04-27
feature_id: 017
---

# Closeout

Open. This feature was split out on 2026-04-26 so KG-specific bitemporal claim
modeling does not stay hidden inside Feature 012.

Progress on 2026-04-27:

- Confirmed Feature 017 is the global/domain KG track, not agent-memory KG.
- Recorded current GraphMERT checkpoint status: official code/datasets exist,
  no confirmed public production checkpoint was found.
- Added a lightweight KG extraction smoke path in `python-backend/kg_pipeline`
  so downstream retrieval work can test KG candidates before the full
  bitemporal persistence/projection layer exists.
- Set NornicDB/nonicdb as the first projection target in docs and env examples.
- Added Alembic migration `030_global_kg_bitemporal_claims` with
  `kg_entities`, `kg_claims`, `kg_claim_evidence`, access stats and
  `kg_projection_outbox`.
- Added `memory_engine.global_kg` helpers for canonical entity keys, conflict
  keys, claim IDs, decay scoring and NornicDB projection payloads.
- Added `memory_engine.global_kg_store` with in-memory smoke mode and a
  Postgres-backed facade that writes entities, claims, evidence and NornicDB
  projection-outbox events.
- Added `kg_pipeline.sinks.global_kg` so extraction results can become
  evidence-linked claim proposals without being silently promoted.
- Added KG pipeline `/propose`, which exposes claim proposals separately from
  extraction and keeps persistence explicit.

Close only when:

- KG bitemporal claim schema is implemented and tested.
- Corrections preserve historical truth and current-truth queries are safe.
- Retrieval combines semantic similarity with temporal/access decay.
- KG claims require evidence refs before promotion.
- Memory-Fusion integration proposes claims without silently promoting them.
- Control UI can inspect claim status, validity, history and provenance.
