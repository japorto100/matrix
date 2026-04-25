---
title: Scheduler, Skills, Formal Planning and Automation Tasks
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-25
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
- [x] T032 Verify disabled skills are filtered via current preference path.
- T033 Verify real LLM refinement with `AGENT_SKILL_REFINEMENT=true`.
- T034 Verify real LLM iterative search.
- T035 Verify real LLM offline refinement.
- [x] T036 Static-test general/task-specific metadata survives parsing.
- [x] T037 Static-test `api_version` and assets survive file parsing and DB row
  mapping shape.
- T038 Live-verify skill DB seed and loader source modes against Postgres.
- T039 Live-verify `api_version` and assets survive DB roundtrip.

## Skill Feedback And Promotion

- T040 Verify audit events for skill_found/refined/used.
- T041 Verify usage counters on real sessions.
- T042 Run trigger-quality CLI against production-like audit data.
- T043 Implement or defer Hindsight outcome feedback.
- T044 Implement or defer skill compliance judge.
- T045 Implement or defer promotion pipeline.
- T046 Verify Pareto with >20 real usage events before relying on it.
- T047 Build or defer `experiments/skill_eval` A/B variants.

## Plan Skill

- [x] T050 Static-test plan skill triggers on DE and EN planning cues.
- [x] T051 Static-test plan skill response is read-only.
- T052 Live-verify execution waits for explicit user confirmation.

## PDDL

- T060 Choose or defer first PDDL pilot workflow.
- T061 Choose or defer solver stack.
- [x] T062 Define refusal/repair loop before any execution integration.
- T063 Keep PDDL out of trivial CRUD and low-latency paths.

## DSPy

- T070 Run/document G(-1).1 LLMSelector architectural match.
- T071 Run/document G(-1).2 MIPROv2 PoC.
- T072 Defer D-2/D-3 schema/interface until benchmark winner.
- T073 Defer A/B variant until N-way bucketing and artifact hash exist.

## Verify Gates

- Scheduled task fires.
- [x] Skill retrieval returns expected skill in static finder/loader tests.
- Prompt scanner protects scheduled task prompt.
- Plan skill does not execute side effects.
- [x] PDDL/DSPy status is explicitly gated.
