---
title: Memory, Context, World Model and Personal KB Tasks
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-30
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
- [x] T011 Live-verify `memory_fusion` Postgres retain path.
- [x] T012 Static-test raw user input is evidence, not observation/truth.
- [x] T013 Static-test agent output is secondary artifact metadata where
  applicable.
- [x] T014 Static-test derived memory has evidence/source backlinks.
- [x] T015 Design durable MemPalace/verbatim drawer schema in Postgres/pgvector
  (`agent.mempalace_drawers`).
- T016 Add or defer DB-level source/status fields.
- [x] T017 [done-static] Add Memory Operation Logging and diff/evidence trace
  correlations.
  - 2026-04-30: provider-free `knowledge-contract` now requires memory
    recall/retain traces to carry `source_status`, `raw_evidence_ref`,
    `operation_log_id` and `diff_ref` before cross-feature context use.
  - 2026-04-30: `memory_fusion` retain builders now persist provider-free
    evidence trace fields; recall metadata and audit payloads preserve them so
    RAG/KG/Semantic context cannot consume untraceable memory by accident.
- T018 Add or defer MemoryAccessPolicy by agent/consumer.
- T019 Add or defer PII/deletion path across tiers.
- T020 Define Hindsight learning-memory boundaries: durable facts,
  preferences, corrections, summaries, reflections and evolving beliefs.
- T021 Rename or document `memory_fusion` as memory orchestration in user-facing
  docs and internal specs.
- T022 [partial-static] Verify Hindsight's KG-like/structured-memory behavior
  in Postgres and document that it stays inside the agent-memory lane, not the
  global KG. Feature 016 now has boundary scenarios forbidding global KG/
  nonicdb as an agent-memory substitute; live Hindsight internals still need
  dedicated verification.
- T023 Review current Hindsight docs/repo state for new schema, runtime or
  eval concepts before finalizing the Matrix Postgres adaptation.
- [x] T024 [done-static-live-smoke] Verify Matrix room/thread/session identity
  is available for durable memory writes and deletion semantics. MemPalace
  Postgres now lists by room/thread/session metadata and refuses unscoped bulk
  deletes; scoped room+thread+session deletion was live-tested against local
  pgvector Postgres.

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
- [x] T039k [done-static-live-smoke] Evaluate MemPalace warmup/embedding
  latency; live probe still shows first-call `memory_add` around 17-22s with
  remote embeddings, which is under the current 30s tool timeout but too close
  for production comfort. Pre-compaction/pre-compression archive writes now use
  the verbatim route and can persist immediately with deferred embeddings
  (`embedding_status=pending`) before later hydration.
- [x] T039k.1 Deduplicate explicit memory writes within a single assistant
  turn/thread window: Meta-Harness `run-eeb4e11fab0f` passed trace gates but
  showed repeated `memory_add` calls for the same exact lifecycle probe,
  increasing latency and token use without adding evidence value. Rerun
  `run-22d2dfd38755` verified one write per memory scenario and lower
  token/latency cost.
- [x] T039l Make automatic post-answer `memory_retain_node` verbatim-first:
  write exact conversation evidence synchronously to MemPalace/Postgres and
  dispatch Hindsight summary retain asynchronously, matching explicit
  `memory_add` behavior.
- [x] T039m Add answer-format hardening after tool calls: Meta-Harness observed one
  OpenRouter-Free turn returning `<tool_call>` markup as assistant text after a
  successful `memory_add`; trace gates passed, but user-facing output should be
  cleaned or retried.
- [x] T039n Fix LangGraph/OpenAI tool-result message serialization after
  Meta-Harness exposed `messages[5]: missing field tool_call_id` on a
  post-`memory_search` LLM call; keep legacy `tool_use_id` while adding
  OpenAI-compatible `tool_call_id`.
- [x] T039o Guard Memory-Fusion/Hindsight live runs against upstream
  `hindsight_api` dotenv side effects: explicit runtime DB URLs must win after
  Hindsight imports, and Meta-Harness live probes should set
  `PYTHON_DOTENV_DISABLED=true` when using controlled process env.
- [x] T039p [done-static-live-smoke] Add a background hydration worker for MemPalace rows with
  `embedding_status=pending`; pending rows are durable/listable immediately but
  semantic recall intentionally ignores them until embeddings are attached.
- T039q Add MemMachine-style ground-truth preservation gates: exact visible
  session text, tool input/output evidence, room/thread/session refs and source
  timestamps must exist before any summary-only Hindsight retain is considered
  successful.
  - 2026-04-30: `knowledge-memory-ground-truth-preserved` covers the static
    Meta-Harness contract for durable raw evidence refs. Full live-runner
    stress remains open.
- [x] T039r [done-static-live-smoke] Add a hydration-worker design and smoke: pending MemPalace rows are
  picked up, embedded with the configured provider, dimension-checked against
  the active index and marked failed with reason instead of silently skipped.
- T039s Add context-injection evals comparing Hindsight-only,
  MemPalace-verbatim-only and Fusion answers for the same task. This is not a
  competition between systems; it determines when exact session evidence must
  constrain derived memory.
  - 2026-04-30: first static cross-feature check exists in
    `knowledge-contract`; full shared-corpus Hindsight/MemPalace/Fusion
    comparison remains open.

## Runtime Context

- T040 Live-verify prompt assembly order against `context/merge.py` and current
  runner path.
- [x] T041 [done-static] Verify 80% pre-save fires before 85% compaction.
- [x] T042 [done-static] Verify 95% emergency compression invokes bounded
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
- [x] T050 [done-static-live-smoke] Verify pre-save runs before both normal
  compression and context compaction, with MemPalace archival receiving the
  complete visible context.
- [x] T051 [done-static] Verify compression/compaction thresholds use
  provider/model context window metadata instead of hardcoded defaults where
  available.

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
- T088 Add visual memory handoff to Feature 028: screenshot/document evidence
  can create sourced summaries, not unsourced memories.
- T089 Add semantic-layer handoff to Feature 025 so personal corrections do not
  silently mutate global metric/term definitions.
  - 2026-04-30: `knowledge-semantic-correction-review-proposal` proves the
    handoff shape: user feedback creates a reviewed semantic correction
    proposal, not a silent truth mutation.
- T090 Add browser-local retrieval handoff to Feature 026 for private/local
  prefiltering before backend memory/RAG calls.

## 2026-04-30 Delegation Memory Additions

- T091 Add parent-side delegation memory curation contract with child session
  id, task id, source refs, confidence/degradation and retain/skip decision.
- T092 Ensure child/subagent runs cannot write durable shared memory by default.
- T093 Emit runtime events for memory retain/recall/curation decisions that
  Feature 033 and Feature 029 can display.
- T094 Add Meta-Harness scenario where delegated evidence is summarized by the
  parent before any memory write.

## Verify Gates

- Memory API returns real data or healthy empty state.
- Context API exposes expected prompt/context metrics.
- Compaction path preserves provenance expectations live.
- [x] KB/world artifacts are rejected from default personal-memory write path.
- [x] World/KB status is not ambiguous.
