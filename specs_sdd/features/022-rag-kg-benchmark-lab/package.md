---
title: RAG/KG Benchmark Lab Package
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 022
---

# Package

## Current Package / Ist

- `python-backend/retrieval/evals/benchmark_lab.py`
- `python-backend/retrieval/evals/canaries.py`
- `python-backend/meta_harness/retrieval_benchmark.py`

## Proposed Package / Soll

- Keep benchmark logic under `retrieval/evals`.
- Keep Meta-Harness artifact writing under `meta_harness`.
- Add candidate adapters in a narrow layer so LightRAG/HippoRAG dependencies do
  not contaminate core retrieval imports.
- Feature 023 writes optimized candidate configs; Feature 022 measures them.
