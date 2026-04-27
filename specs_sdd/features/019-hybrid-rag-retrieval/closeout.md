---
title: Hybrid RAG Retrieval Closeout
status: open
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
---

# Closeout

Open.

Progress on 2026-04-27:

- Added provider-configurable remote embeddings for ingestion with an
  OpenRouter/OpenAI-compatible provider.
- Kept deterministic embeddings as the default `.env.example` smoke path.
- Made sentence-transformer downloads opt-in and pointed HF cache to
  `/mnt/cold-storage/models/huggingface`.
- Added a lightweight KG extraction service path so Feature 019 has a KG-side
  candidate source while Feature 017 continues to own persistence/projection.
- Documented NornicDB/nonicdb as the first graph projection target; FalkorDB is
  not the initial Matrix path.
- Added the first retrieval baseline in `python-backend/retrieval`: deterministic
  intent routing, vector/KG RRF fusion, Context Bubble composition and
  source-reference output.
- Added a mockable adapter from `memory_engine.VectorStore` into retrieval
  hits, so live Chroma/pgvector search can attach without changing the public
  retrieval contract.
- Added a deterministic citation/support verifier that catches unsupported
  answer sentences against retrieved hits. This is not the final LLM Self-RAG
  pass, but gives the pipeline a cheap first safety gate.
- Added a mockable global KG claim-search adapter so Feature 017 Postgres/
  NornicDB claim rows can become fused RAG candidates through the same API.
- Wired selected KG-hit access telemetry at retrieval output time: access stats
  are recorded only for KG claims that survive ranking and Context Bubble
  selection.

This feature can close when Matrix has a tested retrieval layer with
provider-configurable embeddings, vector/KG/fused retrieval modes, Context
Bubble assembly, citation verification and canary evals showing when graph
retrieval earns its cost.
