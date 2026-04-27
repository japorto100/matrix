---
title: RAG/KG Benchmark Lab Research
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
---

# Research Notes

The local GraphRAG benchmark paper is important because it argues against a
blanket "GraphRAG is always better" rule. Matrix should treat graph retrieval
as a query-class-specific candidate: useful for multi-hop/world-relation
questions, dangerous when it bloats context or loses document nuance.

Initial candidate ordering:

1. Matrix vector-only and fused vector+KG baselines.
2. LightRAG-style practical graph retrieval.
3. HippoRAG2-style associative/multi-hop retrieval.
4. LinearRAG/E2GraphRAG only after setup feasibility is proven.

Production recommendation must come from benchmark evidence, not community
hype or framework size.
