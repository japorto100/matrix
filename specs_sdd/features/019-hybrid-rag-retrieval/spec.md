---
title: Hybrid RAG Retrieval
status: implementation_started
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
migrated_from:
  - _ref/Researchwatcher/README.md
  - _ref/Researchwatcher/paperwatcher/core/rag_pipeline.py
  - _ref/Researchwatcher/paperwatcher/core/hybrid_retriever.py
  - _ref/Researchwatcher/kg-module/ARCHITECTURE.md
  - main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md
  - arXiv:2604.09666
---

# Hybrid RAG Retrieval

## Current State / Ist

Matrix already has an ingestion worker, chunkers, embedders, Hindsight sink and
a KG-pipeline hook. Researchwatcher contains a more complete HiRAG shape:
intent routing, hybrid KG/text retrieval, Context Bubble, Self-RAG,
citation verification, RAPTOR-style summaries and LightRAG/KG-module notes.

The current Matrix implementation is not yet organized as a tested RAG system.
KG, vector retrieval, memory retrieval and document ingestion are mixed in
older notes and partial code. Feature 017 owns the global KG/claim model.
Feature 019 owns answer-time RAG retrieval and context assembly over documents,
vectors, KG candidates and citations.

## Target State / Soll

Matrix RAG is a small composable retrieval layer, not a monolithic Haystack,
LlamaIndex, Onyx or RAGFlow deployment. Those remain references only.

The first production line is:

`query -> intent/router -> vector/BM25 retrieval -> optional KG candidate/path retrieval -> late fusion -> context bubble -> generator -> self/citation verification`

Adopt:

- LightRAG-style graph retrieval as practical baseline and implementation
  inspiration.
- HippoRAG2-style associative/memory retrieval as benchmark candidate.
- LinearRAG as relation-free graph construction candidate for scale and lower
  LLM extraction cost.
- GraphRAG-Bench/RAGSearch style evals before making graph retrieval default.
- Researchwatcher Context Bubble, Self-RAG and citation-verifier patterns.

Do not adopt:

- A huge framework as the core architecture before Matrix's retrieval contract
  is measurable.
- GraphRAG for every query type. Dense/hybrid RAG remains the baseline for
  simple/general QA.
- FalkorDB as first graph target. Feature 017's first graph projection target
  is NornicDB/nonicdb.

## Boundary To Feature 017

Feature 017 produces and stores global/domain KG claims and graph projections.
Feature 019 decides when and how to retrieve those claims during answer-time
RAG. Raw document chunks, vector hits, KG claims and graph paths remain separate
artifacts joined by provenance.

## Closeout Criteria

- RAG retrieval can run vector-only, KG-only and fused modes.
- Retrieval results include source/chunk refs and KG claim/path refs when used.
- Context Bubble assembly is deterministic and auditable.
- Self-RAG/citation verification reports unsupported claims.
- Evaluation can compare dense, LightRAG-style, HippoRAG2-style and fused
  retrieval on a small trading/geopolitical canary set.
