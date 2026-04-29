---
title: RAG/KG Benchmark Lab
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
depends_on:
  - 016-meta-harness-agent-optimization
  - 017-knowledge-graph-bitemporal-claims
  - 019-hybrid-rag-retrieval
  - 021-ingestion-paperwatcher-researchwatcher
migrated_from:
  - docs/papers/knowledgegraph/Do We Still Need GraphRAG Benchmarking RAG and GraphRAG for Agentic Search Systems arXiv 2604.09666.md
  - specs_sdd/features/019-hybrid-rag-retrieval/research.md
---

# RAG/KG Benchmark Lab

## Current State / Ist

Feature 019 has the production retrieval shape and early static tests. Feature
017 has KG claim/path primitives and NornicDB/nonicdb projection as the first
graph-backend line. Feature 016 can run Meta-Harness scenarios and trace gates.

What is missing is a dedicated benchmark lane that compares retrieval methods
under matched budgets before Matrix promotes graph retrieval, agentic search or
an external RAG method as a default.

## Target State / Soll

The benchmark lab evaluates retrieval candidates without forcing framework
lock-in:

- dense/vector-only baseline.
- BM25/sparse or hybrid lexical+dense baseline.
- Feature 019 fused vector+KG RRF baseline.
- LightRAG-style graph retrieval baseline.
- HippoRAG2-style associative/multi-hop baseline.
- LinearRAG/E2GraphRAG style methods as tracked candidates when practical.
- GraphRAG-Bench/RAGSearch style comparison rules for when graph helps.

All candidates run through the same canary questions, source corpus, retrieval
budget, context token budget, model/provider budget and scoring harness.

The lab is not the production retrieval path. It produces evidence for Feature
019 and Feature 017 decisions.

## Evaluation Shape

Minimum metrics:

- Recall@k and nDCG@k for retrieved chunks/claims.
- answer faithfulness and unsupported-claim rate.
- citation/source attribution completeness.
- multi-hop path completeness for KG cases.
- latency and offline indexing/update cost.
- provider/token cost.
- failure mode notes: stale data, graph overreach, dense false positives,
  unsupported synthesis, prompt-stuffed graph neighborhoods.

## Closeout Criteria

- Canary set exists for trading, geopolitical, research-paper and simple QA.
- At least vector-only, fused Matrix KG/RAG and one external GraphRAG-like
  candidate can be compared.
- Results are artifacted under Meta-Harness/eval directories with configs.
- Promotion decisions feed back into Feature 019/017 tasks and ADRs.
