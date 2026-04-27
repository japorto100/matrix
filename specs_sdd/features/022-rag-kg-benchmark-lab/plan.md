---
title: RAG/KG Benchmark Lab Plan
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
---

# Plan

1. Define a small canary corpus from local papers, docs and seeded KG claims.
2. Define canary questions for vector-only, KG-helpful and graph-danger cases.
3. Build a runner adapter that calls Feature 019 retrievers under fixed budgets.
4. Add candidate adapters for LightRAG/HippoRAG2 only after local setup is
   proven feasible.
5. Feed metrics into Meta-Harness artifacts and Pareto/decision logs.
6. Use results to promote or defer graph retrieval defaults.
