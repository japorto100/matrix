---
title: RAG/KG Benchmark Lab Tasks
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
---

# Tasks

## Corpus And Questions

- T001 Create canary corpus from `docs/papers/knowledgegraph/`, selected Matrix
  docs and seeded trading/geopolitical KG claims.
- T002 Create question classes: simple factual, document-grounded, multi-hop
  KG, temporal/current-data and graph-overreach negative cases.
- T003 Record source/citation goldens and expected KG path/claim refs.
- T004 Keep search set and holdout set separate for benchmark tuning.

## Candidate Adapters

- T010 Add Matrix vector-only adapter.
- T011 Add Matrix fused vector+KG adapter.
- T012 Add KG-only/path adapter for Feature 017.
- T013 Add LightRAG adapter or shell harness after dependency review.
- T014 Add HippoRAG2 adapter or shell harness after dependency review.
- T015 Track LinearRAG/E2GraphRAG as deferred candidates until there is a
  stable local repo/pipeline worth testing.
- T016 Use NornicDB/nonicdb as the first graph projection target for Matrix KG
  tests; FalkorDB/Neo4j remain comparison references only.

## Metrics

- T020 Implement Recall@k and nDCG@k over chunk/claim refs.
- T021 Implement citation completeness and unsupported-claim checks.
- T022 Implement multi-hop path completeness checks.
- T023 Record offline indexing/update cost and online retrieval latency.
- T024 Record model/provider/token config, especially OpenRouter embedding
  model and dimension.
- T025 Feed benchmark summaries into Meta-Harness candidate artifacts.

## Meta-Harness Integration

- T030 Add Meta-Harness scenarios where simulated users ask paper/trading/KG
  questions and trace gates assert retrieval route, sources and memory/KG
  boundaries.
- T031 Add Pareto candidates for retrieval mode and embedding dimension.
- T032 Add decision ledger entries when graph retrieval is kept, rejected or
  deferred for a query class.
- T033 Ensure benchmark improvements do not become simulation-only hacks:
  candidates must pass holdout and live/provider smokes before promotion.

## Verification

- T040 Run local deterministic benchmark with mock embeddings/fixtures.
- T041 Run OpenRouter-embedding benchmark when credits/rate limits allow.
- T042 Run Postgres/pgvector benchmark for Matrix retrieval.
- T043 Run NornicDB/nonicdb projection benchmark when graph projection path is
  ready.
- T044 Compare at least vector-only vs fused Matrix RAG before enabling KG
  retrieval by default for any query class.
