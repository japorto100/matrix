---
title: Ingestion, Paperwatcher and Researchwatcher
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 021
depends_on:
  - 017-knowledge-graph-bitemporal-claims
  - 019-hybrid-rag-retrieval
migrated_from:
  - _ref/Researchwatcher/
  - _ref/Researchwatcher/researchwatcher.md
  - _ref/Researchwatcher/paperwatcher/
  - python-backend/ingestion/
---

# Ingestion, Paperwatcher and Researchwatcher

## Current State / Ist

Matrix has a Python ingestion package, storage sinks, KG-pipeline hooks and
partial document/chunk plumbing. `_ref/Researchwatcher` adds a richer research
workflow: paper discovery/download, citation-aware search, synthesis hooks,
MCP tests and a RAG/KG-oriented paperwatcher UI/API shape.

Right now ingestion, RAG retrieval and KG promotion are too easy to conflate.
Feature 021 owns the pipeline that turns external documents, papers, APIs and
research feeds into normalized source artifacts. Feature 019 owns answer-time
retrieval over those artifacts. Feature 017 owns global KG claim promotion and
projection after extraction/provenance gates.

## Target State / Soll

Ingestion becomes a reproducible source-to-artifact pipeline:

`source connector -> fetch/download -> normalize -> parse -> chunk -> metadata -> embedding job -> optional IE/KG proposal -> durable artifact refs`

The source artifact is authoritative for provenance. Vector chunks, citation
records and KG claim proposals point back to it. No raw paper, web page, PDF,
API response or tool output is silently promoted into global KG truth.

Researchwatcher/Paperwatcher is used as a reference for:

- paper search/download orchestration.
- citation metadata and source refs.
- research synthesis workflow.
- MCP/API test style for research surfaces.
- RAG/KG integration ideas that are adopted only after Matrix contracts are
  explicit.

Do not adopt blindly:

- its frontend as a primary Matrix surface.
- FalkorDB/KG backend assumptions; Matrix first targets Postgres source
  records and NornicDB/nonicdb projection for global KG.
- any hidden framework dependency that makes ingestion hard to run on the
  local machine.

## Boundaries

- Feature 021: source ingestion, parsing, artifact registry, document metadata,
  chunk metadata, paper/research workflow.
- Feature 019: retrieval, Context Bubble, fused RAG, citation verification.
- Feature 017: bitemporal global KG claims, claim status, evidence backlinks,
  NornicDB/nonicdb projection.
- Feature 012: personal memory, Hindsight, MemPalace and session evidence.

## Closeout Criteria

- Ingestion artifacts have stable source ids, source URIs, content hashes and
  provenance metadata.
- Paperwatcher-like flows can fetch/index at least one local paper and one URL
  source without requiring frontend or Go.
- Chunk metadata includes embedding version, chunk type, citation/source refs
  and optional entity signatures.
- KG proposal output is explicit and reviewable; promotion remains Feature 017.
- RAG retrieval can consume the produced chunks through Feature 019 interfaces.
