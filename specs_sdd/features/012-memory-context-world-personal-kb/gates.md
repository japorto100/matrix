---
title: Memory, Context, World Model and Personal KB Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-30
feature_id: 012
---

# Gates

## 2026-04-29 Visual/Semantic Follow-Up

- Visual evidence from Feature 028 remains source-linked and confidence-gated
  before memory injection.
- User semantic corrections become Feature 025 proposals, not silent global
  truth mutations.
- 2026-04-30: provider-free `knowledge-contract` covers both points as static
  gates: memory evidence must carry durable raw refs before context injection,
  and semantic corrections remain review proposals.

## G1 Personal Memory / Fusion

- [x] `memory_fusion` unit tests pass.
- [x] Raw user input remains evidence/chat-turn metadata, not truth.
- [x] Derived memories require provenance and carry grounding/status metadata.
- [x] KB/world artifacts are rejected from the default personal-memory retain
  path.
- [x] MemPalace Postgres/pgvector retain/list/get/recall smoke is verified with
  deterministic embeddings.
- [x] MemPalace pending-embedding rows are durable/listable immediately and can
  be hydrated later; hydration dimension/provider failures are stored as
  `embedding_status=failed` with reason.
- [ ] Full Hindsight/Fusion Postgres retain/recall live path is verified.

## G2 Runtime Context

- [x] Context policy tests pass.
- [x] Legacy source/layer normalization is tested.
- [x] Ungrounded derived context is filtered or downgraded.
- [x] Degradation flag logic is tested.
- [x] Explicit memory tools expose retain/recall audit metadata for
  Meta-Harness route/provider gates.
- [x] Provider-free Meta-Harness memory/context smoke validates Fusion route,
  Hindsight+MemPalace provider metadata and `memory_search` success without
  consuming LLM quota.
- [x] Provider-free knowledge contract validates Memory-Fusion source status,
  raw evidence refs, operation log ids and diff refs before cross-feature
  KG/RAG/Semantic use.
- [x] Memory-Fusion runtime stores and surfaces `source_status`,
  `raw_evidence_ref`, `operation_log_id` and `diff_ref` on retain/recall paths;
  audit logging carries the same trace keys.
- [ ] Prompt assembly order is live-verified against the current runner path.

## G3 Compaction / Metadata

- [x] Compaction middleware tests pass.
- [x] Message metadata carries source-layer/degradation fields in runner code.
- [ ] 80/85/95 percent thresholds are live-verified with a real long thread.
- [ ] Evidence/provenance preservation after compression is live-verified.

## G4 Memory Backends / Evals

- [x] Context engine, memory provider, KG store and vector store tests pass.
- [ ] Hindsight/MemPalace/Fusion runners execute against the shared corpus.
- [ ] OpenRouter embedding defaults are quality/cost-gated before production
  MemPalace writes use remote embeddings broadly.
- [x] Dev/Meta-Harness has an explicit no-network deterministic 384d embedding
  lane for orchestration and trace gates; it is not a production recall-quality
  default.
- [ ] Hindsight and MemPalace share one evaluated embedding dimension or have
  explicitly separated indexes plus a reset/re-embedding migration plan.
- [ ] Reranker strategy is Pareto-evaluated (`rrf`, local cross-encoder,
  remote/TEI/Cohere/LiteLLM) before any local-weight reranker becomes default.
- [ ] Public benchmark adapters are wired to real downloaded datasets or
  explicitly deferred.
- [ ] Production hybrid fallback remains disabled until real-data eval passes.

## G5 World Model / Personal KB

- [x] World and KB are explicitly separated from default personal memory.
- [ ] World evidence/claim source schemas are selected and implemented.
- [x] KG bitemporal claim graph semantics are moved to Feature 017.
- [x] World evidence/claim first schema slice is selected.
- [ ] Personal KB namespace/store and capture flows are selected and
  implemented.
- [x] Personal KB namespace/store and first note/link/file capture slice are
  selected.
- [ ] Control UI Inbox/Library/Document/Note surfaces are aligned with Feature
  010.

## G6 Delegation Memory

- Subagent/child runs have no default direct write path into durable personal,
  world or KG memory.
- Parent memory curation records child session id, task id, source refs,
  confidence/degradation and retain/skip result.
- Delegation summaries are evidence for parent decisions, not global truth.
- [x] Memory runtime events redact content while preserving trace refs.
  - 2026-04-30: memory recall/retain events carry bank/role/route/provider,
    source-layer counts, query-gate reason and timeout/degradation metadata
    without raw memory text or assistant response bodies.
