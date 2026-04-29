---
title: Hybrid RAG Retrieval Tasks
status: implementation_started
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
---

# Tasks

## Embeddings

- T001 [done-static] Add provider-agnostic remote embedding support for
  ingestion.
- T002 [done-static] Prefer OpenRouter/OpenAI-compatible embeddings when
  configured.
- T003 [done-static] Keep deterministic embeddings for tests and offline smoke
  runs.
- T004 [done-static] Ensure local sentence-transformer downloads are opt-in and use
  `/mnt/cold-storage/models/huggingface` via `HF_HOME`.
- T005 [done-static] Track embedding model/version/dimension in chunk metadata.
  - 2026-04-27: ingestion source artifacts/chunk metadata and RAG benchmark
    provider snapshots now carry embedding provider/model/dimension without
    hardcoding OpenAI/OpenRouter-only code paths.

## Retrieval Architecture

- T010 [done-static] Define retriever interface: vector-only, KG-only, fused.
- T011 [done-static] Add intent/router policy: text, graph, hybrid, temporal.
- T012 [done-static] Implement RRF fusion baseline over vector and KG
  candidates.
- T013 [done-static-live-smoke] Add Context Bubble builder with structural priors and
  diversity gate.
- T014 [done-static] Add citation/source refs to assembled context.
- T015 [done-static-live-smoke] Add Self-RAG/citation verification pass for generated
  answers.
- T016 [done-static] Add Matrix `memory_engine.VectorStore` adapter behind the
  retrieval API with mockable tests.
- T017 [done-static-live-smoke] Add global KG claim-search adapter behind the
  retrieval API with mockable tests and a Postgres pgvector KG candidate
  smoke.
- T018 [done-static] Record KG access telemetry from retrieval only for claims
  selected into Context Bubble output, not every KG candidate returned by
  search.

## Researchwatcher Adoption

- T020 [done-research] Review `paperwatcher/core/rag_pipeline.py` for
  orchestration patterns.
- T021 [done-research] Review `hybrid_retriever.py` for graph/text merge logic.
- T022 [done-research] Review `context_bubble.py`, `self_rag.py` and
  `citation_verifier.py` for direct adaptation.
- T023 [done-research] Review `kg-module` LightRAG architecture, but map first
  graph target to NornicDB/nonicdb rather than FalkorDB.

## Candidate Frameworks / Benchmarks

- T030 Test LightRAG as practical GraphRAG baseline.
- T031 Test HippoRAG2 as associative memory/multi-hop baseline.
- T032 Track LinearRAG for relation-free graph construction.
- T033 Track E2GraphRAG for efficient graph+tree construction.
- T034 [partial-static] Use GraphRAG-Bench/RAGSearch style comparison before defaulting graph
  retrieval.
- T035 Use Feature 023 inner-loop outputs as retrieval candidates, but require
  Feature 022 holdout/Meta-Harness evidence before promotion.
  - 2026-04-27: Feature 023 inner-loop candidate artifacts now include
    retrieval-budget dimensions (`top_k`, `token_budget`, `max_hits`) plus
    fusion/context-bubble metadata. They are still candidate evidence only;
    holdout/live gates decide promotion.
- T036 [partial-static] Add hierarchy-aware chunking and metadata-enriched
  retrieval as first class candidates; do not compare graph methods only
  against weak naive chunking baselines.
  - 2026-04-27: ingestion now emits deterministic chunk IDs and source/citation
    metadata that retrieval candidates can require. Retrieval ranking itself
    still needs to consume these fields in Feature 019/022.
  - 2026-04-27: KG proposal emission now consumes the same chunk evidence
    metadata and records embedding dimension/reuse flags, preserving a single
    source-grounded ingestion contract before vector/KG fusion experiments.
  - 2026-04-29: `holdout-hierarchy-aware-parser-001` now requires
    parser-candidate profile, hierarchy-aware chunker, section hierarchy,
    page anchor, table count and citation metadata on a dense/vector holdout
    reference.
- T037 Add source-grounding baseline order for implementation: strong
  parser/chunker/citation pipeline first, Matrix vector baseline second,
  Matrix fused vector+KG third, external LightRAG/HippoRAG adapters fourth.
  - 2026-04-27: retrieval benchmark canaries now verify reference-level
    source/citation metadata, so vector/fused candidates are judged against a
    stronger source-grounded baseline before external GraphRAG adapters.
  - 2026-04-27: MarkItDown is now available as an optional lightweight parser
    candidate for source-grounded dense baselines, but remains behind parser
    benchmark gates.
- T038 [done-static] Require every retrieval candidate to declare source
  artifact version, parser version, chunking config, embedding model/dimension
  and KG projection version before Feature 022 scores are comparable.
  - 2026-04-27: ingestion source artifact and chunk metadata now include the
    source/parser/chunker/embedding fields; benchmark adapters still need to
    fail candidates that omit them.
  - 2026-04-27: `retrieval.evals.benchmark_lab` now emits
    `metadata_compatibility` and marks candidate results failed when required
    source-grounding metadata is missing.
  - 2026-04-27: KG proposal candidates now expose evidence-side
    `embedding_dim` and source refs, allowing Feature 022 to reject KG/RAG
    adapters that lose ingestion provenance.

## Verification

- T040 [done-static] Unit-test remote embedding provider response parsing and
  missing-key behavior.
- T041 [done-static] Unit-test lightweight KG extraction service.
- T042 [done-static] Unit-test vector-only, KG-only and fused retrieval result
  contracts.
- T043 [done-static] Canary: trading/geopolitical multi-hop question where KG should improve
  retrieval stability.
- T044 [done-static] Canary: simple/general QA where dense retrieval should remain enough.
- T045 [done-static] Aggregate retrieval canaries with Recall@k, nDCG@k and
  pass-rate metrics before larger RAGChecker/RAGAS/GraphRAG-Bench runs.
- T046 Verify simple document QA does not regress when KG/fused retrieval is
  enabled.
- T047 Verify multi-hop/world-model queries have enough expected path evidence
  to justify LightRAG/HippoRAG-style candidates.
- T048 [done-static] Verify graph retrieval does not degrade simple document-grounded QA
  when parser/chunking quality is held constant.
  - 2026-04-29: holdout canaries now include both `holdout-simple-doc-001`
    and `holdout-hierarchy-aware-parser-001`; both force text/vector mode and
    forbid KG sources, so KG/fused promotion is measured against a stronger
    dense/parser-derived baseline.
- T049 Add Feature 026 browser-local retrieval as a measured candidate lane.
- T050 [partial-static] Add Feature 025 semantic filters/terms to retrieval query planning.
  - 2026-04-29: `semantic-term-tool-success-001` now proves the retrieval
    benchmark can require semantic catalog version, term ids and metric id on
    selected references. Runtime query-planning integration remains open.
- T051 [partial-static] Add Feature 028 visual-layout blocks as retrievable evidence with source
  coordinates.
  - 2026-04-29: `visual-layout-source-coordinates-001` now proves selected
    references can carry page number, bbox, layout block type, OCR confidence
    and image checksum through the Context Bubble benchmark path. Runtime
    visual extraction/search remains Feature 028.
