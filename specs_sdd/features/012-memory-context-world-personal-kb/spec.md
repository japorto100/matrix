---
title: Memory, Context, World Model and Personal KB
status: mixed_active
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
migrated_from:
  - main_docs/root/MEMORY_ARCHITECTURE.md
  - main_docs/root/CONTEXT_ENGINEERING.md
  - main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md
  - main_docs/specs/data/DATA_ARCHITECTURE.md
  - main_docs/specs/data/SOURCE_STATUS.md
  - specs/execution/exec-11-memory-evolution.md
  - specs/execution/exec-memory.md
  - specs/execution/exec-context.md
  - specs/execution/exec-world-model.md
  - specs/execution/exec-personal-kb.md
  - docs/superpowers/findings/2026-04-24-memory-umbrella-boundaries.md
adrs: []
---

# Memory, Context, World Model and Personal KB

## Current State / Ist

Memory has implemented pieces: Hindsight phase 1, working memory, context
engine ports, compaction hooks, `memory_fusion` Postgres path, eval runners and
Control UI inspection paths. World model and personal KB are planning-oriented
contracts. Context assembly is the operational owner for prompt order, caching
and compaction.

Older `main_docs` remain important context here. `MEMORY_ARCHITECTURE.md`
defines M1-M5 storage roles, epistemic separation and KG lane concepts.
`CONTEXT_ENGINEERING.md` defines context consumers, retrieval policies,
relevance scoring, token budgets and multi-source merge semantics. SDD owns the
current task/gate view, but these main docs are explicit source material.

## Target State / Soll

Runtime context is assembled from clear layers: immediate conversation, skills,
personal memory, curated KB, world evidence/claims and policy/security
constraints. Storage, retrieval and prompt composition have separate ownership.
Personal Memory is not a silent dumping ground for KB artifacts or world claims.

## Subfeatures

- Hindsight memory engine
- memory_fusion Postgres runtime path
- MemPalace/Hindsight evaluation and shared corpus
- Context assembly and prompt caching
- Compaction orchestration
- Verbatim archive and fact ingest
- World evidence, claims, KG and adjudication
- Personal KB capture, curation and retrieval
- Memory/control UI contracts
- Degradation flags and provenance metadata

## Gap

- World model and personal KB need implementation scoping.
- Verbatim store schema and production hybrid fallback remain open.
- Per-model context thresholds are deferred to harness/meta-regression.
- World KG backend/promotion gate and Personal KB storage/capture need explicit
  implementation choices.
- Public benchmark adapters are prepared but not wired to real dataset
  downloads.

## Verify

- [ ] Memory runtime inspector shows real backend data.
- [ ] Context assembly order is documented against code.
- [ ] Compaction path retains evidence/provenance as expected.
- [ ] `memory_fusion` rejects KB/world artifacts from the default personal
  memory write path.
- [ ] Personal KB and world model are either scoped or explicitly backlog.

## Closeout Criteria

- This umbrella can close only when subfeatures have independent closeouts or
  are explicitly moved to backlog.
