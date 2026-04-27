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
- T017 Add parser/chunking candidate dimensions from Feature 021:
  PyMuPDF4LLM, Docling, MinerU, hierarchy-aware chunking and metadata
  enrichment.
- T018 Consume Feature 023 AutoRAG/inner-loop candidate artifacts as benchmark
  candidates.
- T019 [done-static-live-smoke] Add candidate metadata compatibility checks so
  vector-only, fused, LightRAG and HippoRAG runs are compared only when source
  corpus, parser, chunker, embedding and KG projection versions are declared.
  - 2026-04-27: Matrix baseline candidates now declare source corpus, parser,
    chunker, embedding model/dimension and KG projection version. Meta-Harness
    retrieval artifacts write `metadata_compatibility` into
    `retrieval_benchmark.json` and `verdicts.json`; missing keys fail the
    candidate verdict. Smoke run `run-rag-metadata-compat-smoke` passed
    metadata compatibility for vector-only, KG-only and fused candidates.
  - 2026-04-27: benchmark-level candidate evaluation now also fails individual
    results when required metadata is missing, so weak baselines cannot pass
    before artifact writing.

## Metrics

- T020 [done-initial] Implement Recall@k and nDCG@k over chunk/claim refs.
  - 2026-04-27: `retrieval.evals.benchmark_lab` compares candidates with
    pass rate, Recall@k, nDCG@k and latency over deterministic canaries.
- T021 Implement citation completeness and unsupported-claim checks.
- T022 Implement multi-hop path completeness checks.
- T023 [partial-done] Record offline indexing/update cost and online retrieval latency.
  - 2026-04-27: benchmark report records per-candidate average retrieval
    latency. Offline indexing cost still open.
- T024 Record model/provider/token config, especially OpenRouter embedding
  model and dimension.
- T025 [done] Feed benchmark summaries into Meta-Harness candidate artifacts.
  - 2026-04-27: `write_benchmark_report()` writes stable JSON suitable for
    Meta-Harness artifact directories.
  - 2026-04-27: `meta_harness.retrieval_benchmark` writes one candidate
    directory per retrieval mode under `data/meta_harness/runs/<run>/candidates/`
    with `retrieval_benchmark.json`, `aggregate.json`, `scores.json` and
    `verdicts.json` for Pareto/proposer inspection.

## Meta-Harness Integration

- T030 Add Meta-Harness scenarios where simulated users ask paper/trading/KG
  questions and trace gates assert retrieval route, sources and memory/KG
  boundaries.
- T031 Add Pareto candidates for retrieval mode and embedding dimension.
- [x] T031a Add Pareto-readable candidates for retrieval mode:
  `matrix-vector-only`, `matrix-kg-only` and `matrix-fused-vector-kg`.
- T032 Add decision ledger entries when graph retrieval is kept, rejected or
  deferred for a query class.
- T033 Ensure benchmark improvements do not become simulation-only hacks:
  candidates must pass holdout and live/provider smokes before promotion.

## Verification

- T040 [done-initial] Run local deterministic benchmark with mock embeddings/fixtures.
  - 2026-04-27: local report written to
    `/tmp/matrix-rag-kg-benchmark-report.json`.
  - Results: `matrix-vector-only` pass_rate `0.5`, Recall@5 `0.5`; `matrix-kg-only`
    pass_rate `0.0`, Recall@5 `0.5`; `matrix-fused-vector-kg` pass_rate `1.0`,
    Recall@5 `1.0`, nDCG@5 `0.8155`.
- T041 Run OpenRouter-embedding benchmark when credits/rate limits allow.
- T042 [ready-live] Run Postgres/pgvector benchmark for Matrix retrieval.
  - 2026-04-27: Matrix Postgres runner now uses dedicated `matrix-postgres`
    container on `:5433` with `vector 0.8.2`; benchmark can rely on Matrix DB
    instead of Tradeview or memory-eval containers.
- T043 Run NornicDB/nonicdb projection benchmark when graph projection path is
  ready.
- T044 Compare at least vector-only vs fused Matrix RAG before enabling KG
  retrieval by default for any query class.
- T045 Compare graph/fused retrieval against a strong hierarchy-aware RAG
  baseline, not only against naive chunks.
- T046 Add holdout canaries where GraphRAG is expected to fail or overreach.
- T047 Add "strong dense baseline" canaries from Feature 021 so graph methods
  are not rewarded for beating only weak naive chunking.
- T048 Add NornicDB/nonicdb projection canaries for temporal, relational and
  multi-hop KG queries once Feature 017 projection replay exists.
