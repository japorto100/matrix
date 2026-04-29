---
title: Hybrid RAG Retrieval Package
status: draft
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 019
---

# Package

## Current Package / Ist

- `python-backend/retrieval/api.py`
- `retrieval/understanders/intent_router.py`
- `retrieval/searchers/vector_store.py`
- `retrieval/searchers/kg_claims.py`
- `retrieval/rerankers/rrf.py`
- `retrieval/composers/context_bubble.py`
- `retrieval/verifiers/citation.py`
- `retrieval/evals/benchmark_lab.py`

## Proposed Package / Soll

- Keep retrieval as a shared backend layer, not inside `agent/`.
- Add adapter modules for external candidates under `retrieval/candidates/`
  or `retrieval/adapters/`.
- Agent should consume retrieval through a narrow context adapter, not by
  importing parser/KG internals.
- Feature 023 may generate configs, but runtime retrieval remains here.
