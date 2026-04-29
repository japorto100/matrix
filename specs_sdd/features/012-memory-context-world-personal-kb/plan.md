---
title: Memory, Context, World Model and Personal KB Plan
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
migrated_from:
  - main_docs/root/MEMORY_ARCHITECTURE.md
  - main_docs/root/CONTEXT_ENGINEERING.md
  - main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md
  - specs/execution/exec-11-memory-evolution.md
  - specs/execution/exec-memory.md
  - specs/execution/exec-context.md
  - specs/execution/exec-world-model.md
  - specs/execution/exec-personal-kb.md
  - docs/superpowers/findings/2026-04-24-memory-umbrella-boundaries.md
adrs: []
---

# Plan

## Architecture

This umbrella owns memory storage/evaluation, runtime context assembly, world
evidence and personal KB boundaries. Subfeatures stay separate but share one
retrieval/runtime contract.
`boundaries.md` is the stable source for default artifact routing.

## Critical Files

- `python-backend/memory_fusion/**`
- `python-backend/experiments/memory_eval/**`
- `python-backend/context/**`
- `python-backend/agent/**memory*`
- `python-backend/agent/middleware/compaction.py`
- `python-backend/agent/middleware/compression.py`
- `python-backend/agent/control/memory.py`
- `python-backend/agent/control/context.py`
- `python-backend/memory_engine/kg_store.py`
- `frontend_merger/src/features/memory/**`
- `frontend_merger/src/features/control/components/ContextTab*`

## Migration Strategy

1. Keep memory, context, world and KB as subfeatures.
2. Treat boundary review as stable and convert it into `boundaries.md`.
3. Move research comparisons into `research.md`.
4. Convert open implementation deltas into tasks.
5. Route UI implementation to Feature 010, but keep backend contracts here.
6. Treat older `main_docs` as architecture references; summarize section-level
   requirements into this feature before implementation touches that area.

## Execution Order

1. Verify existing `memory_fusion` and context inspector paths against live
   backend.
2. Finish Personal Memory missing contracts: verbatim schema, source/status,
   operation logs and access policy.
3. Keep world model and Personal KB as scoped/planned until storage/schema
   choices are made.
4. Only enable production hybrid fallback after real-data eval.
5. Feed context threshold tuning into Feature 014/011 harness data.

## Risks

- Mixing storage ownership with prompt assembly ownership.
- Treating world model/personal KB plans as already implemented.
- Letting KB/world artifacts silently enter Personal Memory.
- Losing details at compaction because pre-save is observational only.
