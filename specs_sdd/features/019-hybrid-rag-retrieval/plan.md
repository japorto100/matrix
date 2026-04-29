---
title: Hybrid RAG Retrieval Plan
status: implementation_started
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
---

# Plan

1. Stabilize ingestion embeddings: remote OpenRouter/OpenAI-compatible
   embeddings first, deterministic fallback for tests, local HF models only
   when explicitly enabled and cached on HDD.
2. Keep KG extraction/projection separate from RAG retrieval. Feature 017
   handles KG claim/projection semantics; 019 consumes them.
3. Port/adapt Researchwatcher's useful RAG shapes: intent router, hybrid
   retriever, Context Bubble, Self-RAG and citation verification.
4. Add a small evaluation harness with vector-only, KG-only and fused modes.
5. Benchmark LightRAG and HippoRAG2/LinearRAG as candidates against Matrix
   canaries before adopting any deeper dependency.

## First Implementation Slice

- Add OpenRouter/OpenAI-compatible embedding provider to ingestion.
- Make KG-pipeline lightweight and functional so ingestion can produce
  candidate KG signals without local ML downloads.
- Create RAG feature docs and gates before building retrieval logic.
- Run local unit tests for embedding provider and KG candidate extraction.
