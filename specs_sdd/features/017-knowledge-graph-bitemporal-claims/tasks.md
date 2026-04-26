---
title: Knowledge Graph Tasks
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 017
---

# Tasks

## Schema

- T000 Define global/domain KG boundary: Feature 017 is for world/trading/
  geopolitical/domain claims, not Hindsight KG-like memory or MemPalace loci.
- T001 Define KG entity table and canonical entity key strategy.
- T002 Define bitemporal claim/relation table with `valid_period` and
  system-version history.
- T003 Define evidence backlink table from KG claims to Memory-Fusion, Personal
  KB and World Evidence refs.
- T004 Define conflict key semantics beyond a single `entity_key`.
- T005 Decide whether overlap handling is append-only query logic or explicit
  split-on-insert; do not use lossy truncation triggers.

## Retrieval

- T010 Define claim embedding text and embedding dimension configuration.
- T011 Implement pgvector candidate retrieval for KG claims.
- T012 Add decay scoring for recency, validity-end and access signals.
- T013 Store access telemetry in event/stats tables, not as per-query hot
  updates on claim rows.
- T014 Add answer-time KG context metadata: status, freshness, confidence and
  provenance refs.
- T015 Define vector chunk metadata contract: `chunk_id`, `source_uri`,
  `embedding_version`, ingest timestamp, TTL/validity metadata and candidate
  entity signatures.
- T016 Implement dual retrieval: vector top-k plus KG entity/claim/path
  expansion.
- T017 Implement deterministic RRF fusion baseline.
- T018 Add optional cross-encoder/MMR re-rank hook.
- T019 Add context builder output for compact graph paths plus chunk/source
  attribution.

## Memory/KG Boundary

- T020 Wire Memory-Fusion as a claim proposal source, not an automatic KG
  promotion path.
- T021 Require raw evidence refs before a derived memory fact can become a KG
  claim.
- T022 Keep personal memory, Hindsight KG-like memory, MemPalace loci, Personal
  KB and global/world KG namespaces separate in write policy and degradation
  flags.
- T023 Add correction scenarios where old KG claims remain historically
  visible but are not retrieved as current truth.

## Projection And UI

- T030 Define rebuildable graph projection contract with nonicdb/NornicDB as
  the first global KG candidate; FalkorDB/Neo4j remain alternatives only if the
  first path fails requirements.
- T031 Define Control UI KG claim detail contract.
- T032 Define promotion/demotion review queue behavior.
- T033 Coordinate `/memory/kg` and provenance graph surfaces with Feature 010.
- T034 Define entity merge review behavior for signature-based merge
  candidates.

## Verification

- T040 Unit-test bitemporal insert/correction/query semantics.
- T041 Unit-test no raw tool output is promoted to KG without explicit claim
  extraction and source refs.
- T042 Unit-test decay ranking with stale, recently accessed and expired-valid
  claims.
- T043 Live-smoke one evidence -> proposed claim -> promoted claim -> KG recall
  path.
- T044 Unit-test vector/KG RRF fusion and attribution.
- T045 Eval Recall@k, nDCG, answer faithfulness and latency on a small hybrid
  retrieval canary set.
- T046 Verify global KG retrieval is not used as an agent-memory rail unless a
  scenario explicitly requests world/domain KG context.
- T047 Add RAGSearch-style comparison: vector-only, KG-only and fused retrieval
  under matched query, context, model and retrieval budgets.
- T048 Add multi-hop trading/geopolitical canaries where global KG/nonicdb is
  expected to improve retrieval stability over dense RAG.
- T049 Track offline KG build/update cost and online latency before promoting
  KG retrieval as default for any query class.
