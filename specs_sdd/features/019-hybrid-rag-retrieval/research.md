---
title: Hybrid RAG Retrieval Research
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
---

# Research

## Current Judgement

There is no single best open-source RAG system. For Matrix, the relevant
class is small, methodical retrieval systems rather than enterprise RAG apps.

Adopt as direct references:

- Researchwatcher HiRAG: intent routing, hybrid retriever, Context Bubble,
  Self-RAG and citation verification.
- LightRAG: practical GraphRAG baseline and graph extraction/query ergonomics.
- HippoRAG2: memory-like associative multi-hop retrieval baseline.
- LinearRAG: relation-free graph construction candidate.

Use as eval references:

- GraphRAG-Bench: when graph structures help over traditional RAG.
- arXiv 2604.09666 / RAGSearch: dense vs GraphRAG under identical agentic
  search protocols.
- RAGAS/RAGChecker/Phoenix/Langfuse style diagnostics for context and
  faithfulness.

## Architecture Implication

Dense/hybrid vector retrieval remains the default baseline. Graph retrieval is
introduced for relational, temporal, multi-hop and world-model questions where
explicit structure earns its offline cost.
