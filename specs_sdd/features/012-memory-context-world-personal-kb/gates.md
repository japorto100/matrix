---
title: Memory, Context, World Model and Personal KB Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 012
---

# Gates

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
