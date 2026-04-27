---
title: RAG/KG Benchmark Lab Eval
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
---

# Eval

## Benchmark Families

- Parser/chunking: PyMuPDF4LLM, Docling, MinerU, hierarchy-aware chunking.
- Retrieval: vector-only, KG-only, fused vector+KG.
- External GraphRAG: LightRAG first, HippoRAG2 second.
- Optimized configs: Feature 023 inner-loop candidates.

## Required Splits

- Search set for tuning.
- Holdout set for promotion.
- Hard negatives for stale facts, unsupported graph paths and over-broad graph
  expansion.

## Metrics

- Recall@k, nDCG@k.
- Citation completeness.
- Unsupported-claim rate.
- Multi-hop path completeness.
- Latency, indexing cost and token/context cost.
- Trace-gate pass rate when run through Meta-Harness.
