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

- T001 [partial-done] Create canary corpus from `docs/papers/knowledgegraph/`, selected Matrix
  docs and seeded trading/geopolitical KG claims.
  - 2026-04-27: deterministic Matrix canary corpus now has explicit
    `source_corpus`, split and tags on each canary. Full paper/doc-derived
    corpus expansion remains open.
- T002 [partial-done] Create question classes: simple factual, document-grounded, multi-hop
  KG, temporal/current-data and graph-overreach negative cases.
  - 2026-04-27: implemented `simple_document_grounded` and
    `multi_hop_temporal` classes plus graph-overreach negative tags.
  - 2026-04-27: added `source_provenance` class for answers that must cite
    source artifact/chunk refs.
- T003 [partial-done] Record source/citation goldens and expected KG path/claim refs.
  - 2026-04-27: canaries record required source refs, chunk/claim refs and
    exact KG path tuples; full citation span rows remain open.
  - 2026-04-27: `source-provenance-001` records source artifact id, source
    URI, chunk id/hash, parser/chunker metadata and `citation_ref`.
  - 2026-04-27: canary expectations can now require metadata keys per selected
    reference, so a result cannot pass by returning the right chunk id while
    dropping source artifact, parser/chunker or citation metadata.
- T004 [done-static-live-smoke] Keep search set and holdout set separate for benchmark tuning.
  - 2026-04-27: `RetrievalCanary.split` separates `search` and `holdout`;
    `DEFAULT_SEARCH_CANARIES` is the Meta-Harness optimization default while
    `DEFAULT_HOLDOUT_CANARIES` contains graph-overreach and multi-hop checks.
    `compare_candidates()` reports per-split summaries and `holdout_pass_rate`.

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
- T017 [partial-static] Add parser/chunking candidate dimensions from Feature 021:
  PyMuPDF4LLM, Docling, MinerU, hierarchy-aware chunking and metadata
  enrichment.
  - 2026-04-29: Feature 021 extraction benchmark artifacts now expose parser
    profiles plus chunker/metadata-enrichment candidate spaces for Feature 022
    to consume. Matched retrieval comparison against those parser-derived
    corpora remains open.
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
- T021 [done-static] Implement citation completeness and unsupported-claim checks.
  - 2026-04-27: deterministic canaries can now attach a generated answer,
    require explicit citations, require cited reference ids, and fail benchmark
    candidates on support-ratio, citation-ratio, unsupported-claim and
    missing-citation defects. This reuses the existing retrieval citation
    verifier instead of adding another evaluator path.
- T022 [done-static] Implement multi-hop path completeness checks.
  - 2026-04-27: canary expectations can require exact KG path tuples, and
    both single-canary and candidate-comparison reports now emit selected
    `kg_paths` plus `missing-kg-path` failures. The trading/geopolitical
    baseline requires the `EU -> SANCTIONS -> Russian oil -> SHIPPING_INSURANCE`
    path.
- T023 [partial-done] Record offline indexing/update cost and online retrieval latency.
  - 2026-04-27: benchmark report records per-candidate average retrieval
    latency. Offline indexing cost still open.
- T024 [done-static] Record model/provider/token config, especially
  OpenRouter embedding model and dimension.
  - 2026-04-27: `meta_harness.retrieval_benchmark` writes a redacted
    `provider_config` into `run.json` and per-candidate
    `retrieval_benchmark.json`: agent model, max output tokens, LiteLLM base
    URL, embedding provider/model/dimension, `k`, token budget, max hits and
    OpenRouter-key presence as a boolean only.
- T025 [done] Feed benchmark summaries into Meta-Harness candidate artifacts.
  - 2026-04-27: `write_benchmark_report()` writes stable JSON suitable for
    Meta-Harness artifact directories.
  - 2026-04-27: `meta_harness.retrieval_benchmark` writes one candidate
    directory per retrieval mode under `data/meta_harness/runs/<run>/candidates/`
    with `retrieval_benchmark.json`, `aggregate.json`, `scores.json` and
    `verdicts.json` for Pareto/proposer inspection.

## Meta-Harness Integration

- T030 [partial-done] Add Meta-Harness scenarios where simulated users ask paper/trading/KG
  questions and trace gates assert retrieval route, sources and memory/KG
  boundaries.
  - 2026-04-27: retrieval benchmark artifacts now include query, split and
    question class in `scenario_set.json`; real agent/user trace scenarios
    remain open.
- T031 [partial-done] Add Pareto candidates for retrieval mode and embedding dimension.
  - 2026-04-27: retrieval mode candidates include split summaries and
    holdout-pass fields for outer-loop decisions. Embedding-dimension
    candidates remain open until provider-budget tests run.
  - 2026-04-27: retrieval mode Pareto sweep now includes the
    `source-provenance-001` search canary; `run-inner-rag-provenance-20260427`
    scored fused Matrix RAG at fitness `0.9754`.
- [x] T031a Add Pareto-readable candidates for retrieval mode:
  `matrix-vector-only`, `matrix-kg-only` and `matrix-fused-vector-kg`.
- T032 [done-initial] Add decision ledger entries when graph retrieval is kept,
  rejected or deferred for a query class.
  - 2026-04-27: `meta_harness.retrieval_benchmark` now writes conservative
    candidate decisions through the existing Meta-Harness decision log for
    KG-bearing candidates. Search-only runs defer graph/fused promotion until
    holdout evidence exists; holdout graph-overreach failures discard; strong
    search+holdout pass can keep with live/provider follow-up.
- T033 [partial-done] Ensure benchmark improvements do not become simulation-only hacks:
  candidates must pass holdout and live/provider smokes before promotion.
  - 2026-04-27: inner-loop artifacts carry protected holdout split metadata;
    promotion is still search-set only until holdout/live provider smokes are
    deliberately run.

## Verification

- T040 [done-initial] Run local deterministic benchmark with mock embeddings/fixtures.
  - 2026-04-27: local report written to
    `/tmp/matrix-rag-kg-benchmark-report.json`.
  - Results: `matrix-vector-only` pass_rate `0.5`, Recall@5 `0.5`; `matrix-kg-only`
    pass_rate `0.0`, Recall@5 `0.5`; `matrix-fused-vector-kg` pass_rate `1.0`,
    Recall@5 `1.0`, nDCG@5 `0.8155`.
  - 2026-04-27: Meta-Harness smoke
    `run-rag-citation-path-smoke` wrote Pareto artifacts with citation/path
    fields. Fused Matrix RAG remained the top candidate with pass_rate `1.0`
    and fitness `0.9631`; vector-only now explicitly fails the missing KG path.
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
- T046 [done-static-live-smoke] Add holdout canaries where GraphRAG is expected to fail or overreach.
  - 2026-04-27: `holdout-simple-doc-001` proves KG/fused retrieval must not
    use a high-scoring irrelevant graph claim for plain document QA.
- T047 [partial-done] Add "strong dense baseline" canaries from Feature 021 so graph methods
  are not rewarded for beating only weak naive chunking.
  - 2026-04-27: the holdout simple-document canary acts as a first dense
    baseline; hierarchy-aware/parser-derived canaries from Feature 021 are
    still open.
  - 2026-04-27: `source-provenance-001` now asserts that selected vector
    references preserve source artifact, chunk hash, parser/chunker and
    `citation_ref` metadata. This upgrades the dense baseline from naive
    chunk-id matching toward source-grounded RAG, but real parser-derived
    hierarchy canaries remain open.
  - 2026-04-27: `url-source-provenance-001` adds a URL/arXiv source canary
    tied to Feature 021 `ingest-url`: selected references must preserve
    `source_uri`, `source_kind=url`, `fetch_method=http`, citation refs and
    parser/chunker metadata. This keeps URL ingestion from drifting below the
    local-file provenance standard.
- T048 [done-static] Add NornicDB/nonicdb projection canaries for temporal,
  relational and multi-hop KG queries once Feature 017 projection replay exists.
  - 2026-04-27: Feature 017 now has a static projection-event replay snapshot
    contract that preserves claim IDs, paths and citation refs. Use that as the
    input contract for the future NornicDB/nonicdb projection canaries; live
    graph projection benchmark remains open.
  - 2026-04-27: `nornicdb-projection-replay-001` now requires a KG candidate
    to expose `projection_target=nornicdb`, projection event id, source
    artifact id, chunk id/hash, citation ref and the expected compact KG path.
    This is a static adapter/canary gate; live NornicDB execution remains T043.
- T049 Add Feature 026 browser-local retrieval benchmark lane.
- T050 [done-static] Add Feature 025 semantic-term benchmark cases.
  - 2026-04-29: `semantic-term-tool-success-001` requires semantic catalog
    version, semantic term ids, metric id, source artifact refs and explicit
    citation of `chunk-semantic-tool-success-rate`.
- T051 [done-static] Add Feature 028 visual-layout evidence benchmark cases.
  - 2026-04-29: `visual-layout-source-coordinates-001` requires page/bbox,
    layout block type, OCR confidence, image checksum and exact citation refs.
- T052 [done-static] Add Feature 027 report-grounding benchmark cases.
  - 2026-04-29: `report-grounding-manifest-001` requires report manifest id,
    output path, renderer and source artifact citation metadata.
