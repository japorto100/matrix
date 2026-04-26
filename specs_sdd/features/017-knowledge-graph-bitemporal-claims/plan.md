---
title: Knowledge Graph Plan
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 017
---

# Plan

## Goal

Split KG from the memory umbrella and implement it as an auditable bitemporal
claim graph. The first implementation should be Postgres-first, with graph
backends treated as rebuildable projections.

## Order

1. Define entity, claim, evidence-link and access-stat schemas.
2. Prove bitemporal correction semantics with tests.
3. Add pgvector candidate search and decay scoring.
4. Wire Memory-Fusion and World Evidence as claim proposal sources.
5. Add promotion/demotion gates and Control UI inspection contract.
6. Decide whether graph projection is needed after Postgres behavior is proven.

## Key Files

- `python-backend/memory_engine/kg_store.py`
- `python-backend/memory_fusion/**`
- `python-backend/agent/control/kg_context.py`
- `frontend_merger/src/features/memory/**`
- `specs_sdd/features/012-memory-context-world-personal-kb/**`
