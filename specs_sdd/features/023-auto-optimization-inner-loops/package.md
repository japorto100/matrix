---
title: Auto-Optimization Inner Loops Package
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 023
---

# Package

## Current Package / Ist

- `meta_harness`: candidate artifacts, Pareto ranking, decisions, scenario
  runner and benchmark import.
- `retrieval.evals`: deterministic RAG/KG canaries.
- `_ref/auto-rag-optimizer`: external/local reference, not integrated.

## Proposed Package / Soll

```text
python-backend/auto_optimization/
  candidates.py
  search_space.py
  experiment_log.py
  artifact_adapter.py
  rag_inner_loop.py
  extraction_inner_loop.py
  memory_inner_loop.py
```

CLI entry points can live under `meta_harness.meta_cli` initially:

```text
meta_cli optimize-rag
meta_cli optimize-extraction
meta_cli optimize-memory
```

This keeps the user-facing workflow under the harness while avoiding a
monolithic Meta-Harness module.
