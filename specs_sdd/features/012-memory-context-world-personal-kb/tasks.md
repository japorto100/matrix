---
title: Memory, Context, World Model and Personal KB Tasks
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-26
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
- [x] T006 Before implementing any main-doc-specific section, summarize the
  relevant section into this feature's tasks/gates.

## Personal Memory

- T010 Verify Hindsight retain/recall/reflect/consolidate live path.
- T011 Live-verify `memory_fusion` Postgres retain path.
- [x] T012 Static-test raw user input is evidence, not observation/truth.
- [x] T013 Static-test agent output is secondary artifact metadata where
  applicable.
- [x] T014 Static-test derived memory has evidence/source backlinks.
- [x] T015 Design durable MemPalace/verbatim drawer schema in Postgres/pgvector
  (`agent.mempalace_drawers`).
- T016 Add or defer DB-level source/status fields.
- T017 Add or defer Memory Operation Logging and diffs.
- T018 Add or defer MemoryAccessPolicy by agent/consumer.
- T019 Add or defer PII/deletion path across tiers.
- T020 Define Hindsight learning-memory boundaries: durable facts,
  preferences, corrections, summaries, reflections and evolving beliefs.
- T021 Rename or document `memory_fusion` as memory orchestration in user-facing
  docs and internal specs.
- T022 Verify Hindsight's KG-like/structured-memory behavior in Postgres and
  document that it stays inside the agent-memory lane, not the global KG.
- T023 Review current Hindsight docs/repo state for new schema, runtime or
  eval concepts before finalizing the Matrix Postgres adaptation.
- T024 Verify Matrix room/thread/session identity is available for durable
  memory writes and deletion semantics.

## Memory Evaluation

- T030 Verify Hindsight runner on shared corpus.
- T031 Verify MemPalace runner on shared corpus.
- T032 Verify orchestration runner on shared corpus.
- T033 Verify long-context smoke with summary/verbatim/orchestration routes.
- [x] T034 Build full eval classes: verbatim, derived, cross-session,
  forgetting.
- [x] T035 Add cost/latency/governance metrics.
- T036 Keep production hybrid fallback disabled until real-data eval passes.
- T037 Wire public benchmark adapters or document why deferred.
- T038 Add MemPalace trigger-policy evals: exact-history, conflict,
  audit/source request, high-risk strategy decision and old-session recovery.
- T039 Add anti-bloat evals proving MemPalace is not injected by default for
  simple current/live-market questions.
- [x] T039a Review MemPalace upstream documentation and git repo freshness before
  schema lock; pull/update `_ref/mempalace` only after checking local changes
  and recording adopted deltas.
- [x] T039b Verify whether upstream MemPalace's SQLite/file-oriented design has
  updated Postgres-compatible concepts; otherwise document Matrix's Postgres
  mapping and divergence.
- [x] T039c Add a Postgres MemPalace persistence proof for session/raw-message,
  tool-output and loci metadata before enabling production archive writes.
- [x] T039d Replace Matrix MemPalace runtime Chroma usage with
  Postgres/pgvector while preserving the Hindsight-compatible async API.
- T039e Evaluate OpenRouter embedding model defaults for quality/cost; free
  model is allowed for dev smoke only until retrieval quality is measured.
- T039f Add credential/redaction/quota audit gate for remote embedding calls
  because MemPalace drawers may contain raw chat and tool output.
- [x] T039g Research upstream MemPalace and Hindsight recommendations for embedding
  model/vector dimension; distinguish vector dimension from MemPalace's
  house/room/drawer hierarchy and record reset/re-embedding requirements.
- [x] T039h Disable local Hindsight reranker as Matrix default for dev and
  Meta-Harness loops (`rrf` baseline); evaluate local/remote rerankers later as
  Pareto candidates instead of loading weights by default.
- [x] T039i Make explicit `memory_add` persist synchronously to MemPalace
  verbatim/Postgres and dispatch Hindsight summary retain in the background so
  exact evidence survives before compaction without blocking the tool timeout.
- [x] T039j Change explicit memory tool defaults: `memory_add` writes
  personal/experience memory by default, maps accidental `world` writes away
  from global-world/KG, and `memory_search` searches all fact types unless a
  type is explicitly requested.
- [x] T039j.1 Normalize invented explicit memory `fact_type` values from LLM
  tool calls: unknown write types become `experience` with
  `original_fact_type` metadata; unknown search filters are omitted.
- T039k Evaluate MemPalace warmup/embedding latency; live probe still shows
  first-call `memory_add` around 17-22s with remote embeddings, which is under
  the current 30s tool timeout but too close for production comfort.

## Runtime Context

- T040 Live-verify prompt assembly order against `context/merge.py` and current
  runner path.
- T041 Verify 80% pre-save fires before 85% compaction.
- T042 Verify 95% emergency compression invokes bounded
  `MemoryManager.on_pre_compress`.
- [x] T043 Static-verify MessageMeta carries context/layer/degradation metadata
  in runner code.
- T044 Verify ContextTab uses live `/api/v1/control/context`.
- T045 Verify Agent Chat surfaces enough context/degradation metadata.
- T046 Route per-model thresholds to harness/meta-regression.
- [x] T047 Add prompt-layout regression for cache-hit/cost when ready.
- T048 Verify Hindsight/profile context can be injected without replacing live
  market/news/source-backed data.
- T049 Verify MemPalace recall requires a trigger and emits source/session refs.
- T050 Verify pre-save runs before both normal compression and context
  compaction, with MemPalace archival receiving the complete visible context.
- T051 Verify compression/compaction thresholds use provider/model context
  window metadata instead of hardcoded defaults where available.

## Global World Evidence And KG Handoff

- [x] T060 Define first `Global World Evidence` and `Claim Layer`
  schemas.
- [x] T061 Decide global KG backend shortlist and first implementation:
  Postgres evidence/claim tables first, graph backend moved to Feature 017.
- [x] T062 Adapt IE pipeline entity/relation/source types for
  trading/geopolitics/macro.
- [x] T063 Define claim status machine and degradation flags.
- [x] T064 Define promotion/demotion gate and audit trail.
- [x] T065 Define answer-time `Retrieve -> Normalize -> Adjudicate -> Compose`.
- [x] T066 Keep world model planned until at least one evidence->claim smoke
  exists.
- [x] T067 Split KG-specific bitemporal claim schema, graph projection and
  decay retrieval into Feature 017.

## Personal KB

- [x] T080 Decide KB namespace/store.
- [x] T081 Define first capture flow for links/webclips.
- [x] T082 Define first capture flow for PDFs/files.
- [x] T083 Define capture flow for YouTube/podcast transcripts.
- [x] T084 Define import flow for Markdown/PKM/bookmarks.
- [x] T085 Define annotations/highlights/labels/pins schema.
- [x] T086 Define KB retrieval policy for context layer.
- [x] T087 Coordinate Inbox/Library/Document/Note surfaces with Feature 010.

## Verify Gates

- Memory API returns real data or healthy empty state.
- Context API exposes expected prompt/context metrics.
- Compaction path preserves provenance expectations live.
- [x] KB/world artifacts are rejected from default personal-memory write path.
- [x] World/KB status is not ambiguous.
