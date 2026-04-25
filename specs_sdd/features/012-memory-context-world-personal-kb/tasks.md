---
title: Memory, Context, World Model and Personal KB Tasks
status: mixed_active
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 012
migrated_from:
  - specs/execution/exec-memory.md
  - specs/execution/exec-context.md
  - specs/execution/exec-world-model.md
  - specs/execution/exec-personal-kb.md
---

# Tasks

## Migration

- [x] T001 Split memory/context/world/personal-KB into task sections.
- [x] T002 Convert boundary review into `boundaries.md`.
- [x] T003 Extract MemPalace/Hindsight/world/KB research into `research.md`.
- [x] T004 Create subfeature contracts in `subfeatures.md`.
- [x] T005 Explicitly map `main_docs` memory/context/RAG/data architecture
  sources into `sources.md`.
- [ ] T006 Before implementing any main-doc-specific section, summarize the
  relevant section into this feature's tasks/gates.

## Personal Memory

- [ ] T010 Verify Hindsight retain/recall/reflect/consolidate live path.
- [ ] T011 Verify `memory_fusion` Postgres retain path.
- [ ] T012 Verify raw user input is evidence, not observation/truth.
- [ ] T013 Verify agent output is secondary artifact.
- [ ] T014 Verify derived memory has evidence/source backlinks.
- [ ] T015 Design or defer durable `verbatim_store` schema.
- [ ] T016 Add or defer DB-level source/status fields.
- [ ] T017 Add or defer Memory Operation Logging and diffs.
- [ ] T018 Add or defer MemoryAccessPolicy by agent/consumer.
- [ ] T019 Add or defer PII/deletion path across tiers.

## Memory Evaluation

- [ ] T020 Verify Hindsight runner on shared corpus.
- [ ] T021 Verify MemPalace runner on shared corpus.
- [ ] T022 Verify fusion runner on shared corpus.
- [ ] T023 Verify long-context smoke with summary/verbatim/fusion routes.
- [ ] T024 Build full eval classes: verbatim, derived, cross-session,
  forgetting.
- [ ] T025 Add cost/latency/governance metrics.
- [ ] T026 Keep production hybrid fallback disabled until real-data eval passes.
- [ ] T027 Wire public benchmark adapters or document why deferred.

## Runtime Context

- [ ] T030 Verify prompt assembly order against `context/merge.py` and current
  runner path.
- [ ] T031 Verify 80% pre-save fires before 85% compaction.
- [ ] T032 Verify 95% emergency compression invokes bounded
  `MemoryManager.on_pre_compress`.
- [ ] T033 Verify MessageMeta carries context/layer/degradation metadata.
- [ ] T034 Verify ContextTab uses live `/api/v1/control/context`.
- [ ] T035 Verify Agent Chat surfaces enough context/degradation metadata.
- [ ] T036 Route per-model thresholds to harness/meta-regression.
- [ ] T037 Add prompt-layout regression for cache-hit/cost when ready.

## Global World Model

- [ ] T040 Define `Global World Evidence`, `Claim Layer`, `Global World KG`
  schemas.
- [ ] T041 Decide global KG backend shortlist and first implementation.
- [ ] T042 Adapt IE pipeline entity/relation/source types for
  trading/geopolitics/macro.
- [ ] T043 Define claim status machine and degradation flags.
- [ ] T044 Define promotion/demotion gate and audit trail.
- [ ] T045 Define answer-time `Retrieve -> Normalize -> Adjudicate -> Compose`.
- [ ] T046 Keep world model planned until at least one evidence->claim smoke
  exists.

## Personal KB

- [ ] T050 Decide KB namespace/store.
- [ ] T051 Define capture flow for links/webclips.
- [ ] T052 Define capture flow for PDFs/files.
- [ ] T053 Define capture flow for YouTube/podcast transcripts.
- [ ] T054 Define import flow for Markdown/PKM/bookmarks.
- [ ] T055 Define annotations/highlights/labels/pins schema.
- [ ] T056 Define KB retrieval policy for context layer.
- [ ] T057 Coordinate Inbox/Library/Document/Note surfaces with Feature 010.

## Verify Gates

- [ ] Memory API returns real data or healthy empty state.
- [ ] Context API exposes expected prompt/context metrics.
- [ ] Compaction path preserves provenance expectations.
- [ ] KB/world artifacts are rejected from default personal-memory write path.
- [ ] World/KB status is not ambiguous.
