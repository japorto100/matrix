---
title: Memory Research And Adoption Notes
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
migrated_from:
  - main_docs/root/MEMORY_ARCHITECTURE.md
  - main_docs/root/CONTEXT_ENGINEERING.md
  - main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md
  - docs/papers/knowledgegraph/
  - specs/execution/exec-memory.md
  - specs/execution/exec-world-model.md
  - specs/execution/exec-personal-kb.md
---

# Research

## Main Docs Carry-Forward

`main_docs/root/MEMORY_ARCHITECTURE.md` is older but still relevant. Adopted
concepts:

- M1-M5 layering: shared cache, KG, episodic store, vector/RAG and working
  memory.
- epistemic separation: user statements, agent inferences, world claims and KB
  artifacts must not collapse into one bucket.
- Fast Lane vs Slow Lane KG growth.
- source persistence and vector ingestion boundaries.
- overlay/claim/evidence/stanced merge concepts.

`main_docs/root/CONTEXT_ENGINEERING.md` remains reference material for:

- context consumer matrix.
- query type to memory layer routing.
- retrieval order and fallback behavior.
- relevance scoring, caps and override/decay.
- token budget allocation and compaction priority.
- multi-source merge, conflict resolution and graceful degradation.
- context trace and quality metrics.

`main_docs/root/RAG_GRAPHRAG_STRATEGY_2026.md` contributes runtime mode and
non-goal framing: search, compare/audit, verify and global/corpus modes are
different retrieval contracts.

## Hindsight vs MemPalace

Hindsight is the agent-memory engine: extraction, reflection, consolidation,
multi-channel search and derived observations. MemPalace is primarily verbatim
conversation retrieval. The useful architecture is not "replace Hindsight", but
evaluate which query classes benefit from verbatim-first retrieval.

Adopted from MemPalace concepts:

- query sanitizer.
- source/provenance refs.
- Method-of-Loci metadata for recall filters.
- verbatim evidence surfacing.
- shared eval route through `memory_fusion`.

Not adopted as current target:

- filesystem MemPalace runtime as production store.
- ChromaDB as primary store.

## Memory For Autonomous Agents Paper

Key adopted implications:

- summarization drift requires verbatim/audit backstop before compaction.
- memory eval must include recall quality, task outcome, cost/latency and
  governance.
- source attribution matters: user statement > agent inference.
- forgetting/privacy is separate from cold archival.
- memory operation logs and diffs are needed for regression testing.

## World Model Research

World model is not personal memory. It needs evidence, claims, status and
adjudication.

Candidate/adopted concepts:

- Fast Lane for temporal/event data with short TTL.
- Slow Lane for structural knowledge with batch validation.
- claim reification before KG promotion.
- evidence-first answer-time composition.
- NornicDB as candidate global KG backend due Bolt/Cypher, temporal decay and
  vector support, subject to maturity evaluation.
- local `docs/papers/knowledgegraph/*` corpus as research input for GraphRAG,
  adaptive retrieval, knowledge conflict and cognitive memory-layer design.

## Personal KB Product References

Recall is useful for capture/product flows. TriliumNext is useful for
outliner/notebook/clipper UX patterns. Neither becomes the backend source of
truth by default.

Adopt patterns:

- inbox/library/save flow.
- document/transcript/note surfaces.
- labels/highlights/pins.
- personal, user-owned feel.

Avoid:

- a second backend truth beside matrix stores.
- manual graph maintenance as the primary workflow.

## Future Research

- Mem0/Letta for stateful memory patterns.
- Ebbinghaus decay instead of fixed cold-migration rules.
- Bayesian/uncertainty-aware retrieval.
- MemoryArena-style active decision-making evals.
- multimodal memory once voice/chart artifacts enter memory.
