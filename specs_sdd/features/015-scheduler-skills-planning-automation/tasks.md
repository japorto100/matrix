---
title: Scheduler, Skills, Formal Planning and Automation Tasks
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-30
feature_id: 015
migrated_from:
  - specs/execution/exec-scheduler.md
  - specs/execution/exec-scheduler2.md
  - specs/execution/exec-skills.md
  - specs/execution/exec-14-pddl-formal-planning.md
  - specs/execution/exec-14-DSPy.md
---

# Tasks

## Migration

- [x] T001 Summarize scheduler Phase 1 closeout in `gates.md`.
- [x] T002 Scope scheduler Phase 2 from `exec-scheduler2`.
- [x] T003 Split skills runtime from feedback/promotion.
- [x] T004 Import ADR-003 DSPy gating.
- [x] T005 Keep PDDL pilot as gated task, not default path.

## Scheduler Phase 1

- T010 Verify scheduled task create/list/pause/resume/cancel/edit/run-now.
- [x] T011 Static-test prompt scanner blocks scheduled-task prompt injection on
  create and edit.
- T012 Verify ownership checks reject cross-user mutation.
- T013 Verify active hard cap and per-turn rate limit.
- T014 Verify NOTIFY hot reload.
- T015 Verify live cron tick end-to-end to Matrix delivery.
- T016 Verify chat-to-DB via Agent Chat UI.
- T017 Verify `/control/tasks` against real DB.

## Scheduler Phase 2

- T020 Decide first Phase-2a slice.
- T021 Implement/verify dep-update Matrix digest if selected.
- T022 Implement/verify email delivery if selected.
- T023 Implement/verify Telegram delivery if selected.
- T024 Implement/verify scheduler metrics endpoint if selected.
- T025 Implement/verify Control-UI inline edit if selected.
- T026 Implement/verify routines/webhooks if selected.
- T027 Implement/verify condition tasks if selected.
- T028 Keep Temporal deferred until saga/replay/human-approval need exists.

## Skills Runtime

- [x] T030 Static-test filesystem/db/hybrid skill loader source modes.
- [x] T031 Static-test finder BM25/dense/RRF with expected-skill queries.
- [x] T031a Add query-gating for general skills and stopword filtering so
  trivial/no-tool turns do not load unrelated skills.
- [x] T031b Add memory-intent skill precision: explicit `memory_add`,
  `memory_search`, remember/recall and context-compaction prompts load
  `memory-usage` without padding `plan`, `market-research` or
  `risk-assessment`.
- [x] T031c Add explainable BM25/RRF skill-search traces for Meta-Harness and
  Control diagnostics.
  - 2026-04-30: `find_skills_with_trace()` returns selected ids, query terms,
    BM25 ranks/scores, dense ranks when used, RRF score, matched terms and
    selection reason without exposing skill body text. `iterative_find()` now
    carries these traces into `skill_found` audit metadata.
- [x] T031d Add non-personal eval/tool-control skill precision so direct
  marker turns and chart-control turns do not load `memory-usage` unless a
  positive memory cue exists.
  - 2026-05-01: Local-8B chart no-allowlist evidence first showed
    `memory-usage` over-selection for `get_chart_state`. The bounded fix
    suppresses memory skills for eval markers and tool-control phrases while
    preserving normal BM25/RRF ranking for trading/chart skills. Unit coverage
    and `run-local8b-floor-chart-no-allowlist-skill-clean-002` verify the path.
- [x] T032 Verify disabled skills are filtered via current preference path.
- T033 Verify real LLM refinement with `AGENT_SKILL_REFINEMENT=true`.
- T034 Verify real LLM iterative search.
- T035 Verify real LLM offline refinement.
- [x] T036 Static-test general/task-specific metadata survives parsing.
- [x] T037 Static-test `api_version` and assets survive file parsing and DB row
  mapping shape.
- [x] T037a Expand skill package asset parsing beyond
  `scripts/examples/templates`: small text/code files in arbitrary subfolders
  are preserved in `assets JSONB` shape and included in import security scans.
- T038 Live-verify skill DB seed and loader source modes against Postgres.
- T039 Live-verify `api_version` and assets survive DB roundtrip.

## Skill Feedback And Promotion

- [x] T040 Verify audit events for skill_found/refined/used.
  - 2026-04-30: Runtime test covers `format_skills_for_prompt_async` emitting
    ordered `skill_found`, `skill_refined` and `skill_used` audit events with
    session/thread ids, selected skill ids, body-redacted search traces and
    coverage metadata.
- [x] T041 Verify usage counters on real sessions.
  - 2026-04-30: Static runtime gate verifies rendered skills increment the
    provider-agnostic filesystem lifecycle sidecar. Live DB roundtrip remains
    tracked by T038/T039.
- [x] T041a Add provider-agnostic filesystem skill lifecycle sidecar so
  non-DB skills get prompt usage counts, view counts, pin state and active
  lifecycle metadata.
  - 2026-04-30: default sidecar path uses XDG state
    (`$XDG_STATE_HOME/matrix-agent/skills/usage.json` or
    `~/.local/state/matrix-agent/skills/usage.json`) instead of writing into
    the source tree.
- [x] T041b Add pinned-skill write fence so GitHub imports and `.skill`
  archives cannot silently overwrite curated/pinned runtime skills.
- [x] T041c Expose skill usage, lifecycle state and pin state through the
  Control skills read model for frontend/control follow-up.
- T041d Live-verify pinned skill protection through Control UI and a real
  import attempt against the dev stack.
- T042 Run trigger-quality CLI against production-like audit data.
- T043 Implement or defer Hindsight outcome feedback.
- T044 Implement or defer skill compliance judge.
- T045 Implement or defer promotion pipeline.
- T046 Verify Pareto with >20 real usage events before relying on it.
- T047 Build or defer `experiments/skill_eval` A/B variants.
- T048 Research online/public skills for trading, geopolitical research,
  strategy review, source-quality/citation workflows and general Matrix-agent
  operations; classify each as adopt, extend, reference-only or reject.
- T049 Define a security and provenance audit checklist before importing any
  third-party skill into the Matrix runtime.
- T050 Compare Hermes-style experience-to-skill learning and EvoSkill-style
  failure-driven skill evolution against Matrix's non-coding domain workflows.

## Plan Skill

- [x] T060 Static-test plan skill triggers on DE and EN planning cues.
- [x] T061 Static-test plan skill response is read-only.
- T062 Live-verify execution waits for explicit user confirmation.

## PDDL

- T070 Choose or defer first PDDL pilot workflow.
- T071 Choose or defer solver stack.
- [x] T072 Define refusal/repair loop before any execution integration.
- T073 Keep PDDL out of trivial CRUD and low-latency paths.

## DSPy

- T080 Run/document G(-1).1 LLMSelector architectural match.
- T081 Run/document G(-1).2 MIPROv2 PoC.
- T082 Defer D-2/D-3 schema/interface until benchmark winner.
- T083 Defer A/B variant until N-way bucketing and artifact hash exist.

## Verify Gates

- Scheduled task fires.
- [x] Skill retrieval returns expected skill in static finder/loader tests.
- Prompt scanner protects scheduled task prompt.
- Plan skill does not execute side effects.
- [x] PDDL/DSPy status is explicitly gated.
