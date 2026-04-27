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
