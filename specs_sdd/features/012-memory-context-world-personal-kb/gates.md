---
title: Memory, Context, World Model and Personal KB Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
---

# Gates

## G1 Personal Memory / Fusion

- [x] `memory_fusion` unit tests pass.
- [x] Raw user input remains evidence/chat-turn metadata, not truth.
- [x] Derived memories require provenance and carry grounding/status metadata.
- [x] KB/world artifacts are rejected from the default personal-memory retain
  path.
- [ ] Postgres retain/recall live path is verified.

## G2 Runtime Context

- [x] Context policy tests pass.
- [x] Legacy source/layer normalization is tested.
- [x] Ungrounded derived context is filtered or downgraded.
- [x] Degradation flag logic is tested.
- [ ] Prompt assembly order is live-verified against the current runner path.

## G3 Compaction / Metadata

- [x] Compaction middleware tests pass.
- [x] Message metadata carries source-layer/degradation fields in runner code.
- [ ] 80/85/95 percent thresholds are live-verified with a real long thread.
- [ ] Evidence/provenance preservation after compression is live-verified.

## G4 Memory Backends / Evals

- [x] Context engine, memory provider, KG store and vector store tests pass.
- [ ] Hindsight/MemPalace/Fusion runners execute against the shared corpus.
- [ ] Public benchmark adapters are wired to real downloaded datasets or
  explicitly deferred.
- [ ] Production hybrid fallback remains disabled until real-data eval passes.

## G5 World Model / Personal KB

- [x] World and KB are explicitly separated from default personal memory.
- [ ] World evidence/claim/KG schemas are selected and implemented.
- [x] World evidence/claim first schema slice is selected.
- [ ] Personal KB namespace/store and capture flows are selected and
  implemented.
- [x] Personal KB namespace/store and first note/link/file capture slice are
  selected.
- [ ] Control UI Inbox/Library/Document/Note surfaces are aligned with Feature
  010.
