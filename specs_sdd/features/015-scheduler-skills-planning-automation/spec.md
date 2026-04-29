---
title: Scheduler, Skills, Formal Planning and Automation
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
  - specs/execution/archive/pddl_phase22b_delta.md
  - docs/superpowers/findings/2026-04-23-adr-003-exec-14-dspy-gating.md
adrs:
  - 0003
---

# Scheduler, Skills, Formal Planning and Automation

## Current State / Ist

Scheduler Phase 1 is implemented and adversarially verified at static/build/unit
level, with live cron/chat/UI gates still on-demand. Scheduler Phase 2 is a
separate extension slice for routines, alternative delivery, condition tasks and
remaining infra jobs. Skills loader/finder/refiner/store/importer/offline
refiner/pareto pieces are largely implemented; Hindsight outcome feedback,
promotion pipeline and real-LLM skill verify remain open. PDDL and DSPy are
gated planning/optimization tracks, not default automation runtime.

Static verification on 2026-04-25 passes Scheduler adapter/service-user tests,
Plan skill tests, Skill Finder tests, Prompt Scanner tests and Skills-Guard
tests. Go scheduler packages also passed in the earlier `go test -tags goolm
./...` appservice run. These checks do not prove live cron tick, NATS delivery
or Matrix delivery. A later static cleanup on 2026-04-25 adds coverage for
skill source modes and loader semantics: filesystem, DB-only and hybrid global
sources; global/team/personal override order; `api_version`, skill type and
asset preservation; and disabled-skill filtering, including the all-disabled
case.

## Target State / Soll

Agent automation has a coherent path: scheduled tasks, skill retrieval and
refinement, formal planning for high-risk workflows and DSPy optimization only
behind explicit gates.

## Subfeatures

- Scheduler phase 1 closeout
- Scheduler phase 2 planning
- Scheduler prompt security and user/task limits
- Skill loader/finder/refiner/store/importer/evolver
- Skill feedback, promotion and Hindsight integration
- Skill eval and compliance scoring
- PDDL formal planning
- DSPy optimization gates
- Planning skill
- Scheduled-task prompt security

## Gap

- Scheduler live cron/chat/UI delivery gates remain open.
- Scheduler Phase 2 delivery/routines/conditions/infra jobs remain open.
- Skills Hindsight feedback/promotion remains open.
- Skills real-LLM refinement/iterative search/offline-refiner verify remains
  open.
- Skills DB roundtrip still needs live Postgres proof; static source-mode and
  row-mapping behavior are covered.
- PDDL is scoped but not an active implementation default.
- DSPy requires ADR-003 gates before broader work.

## Static Verify

- [x] `uv run pytest tests/agent/scheduler tests/agent/skills/test_plan_skill.py tests/agent/test_skill_finder.py tests/agent/security/test_prompt_scanner.py tests/agent/security/test_skills_guard.py -q` passes.
- [x] Scheduler adapter drains SSE and summarizes turns in unit tests.
- [x] Plan skill is loaded and encodes read-only planning behavior.
- [x] Skill source-mode, override, asset/API-version and disabled-filter tests
  pass.
- [x] Prompt scanner and Skills-Guard tests pass.
- [x] PDDL/DSPy are documented as gated, not default runtime.

## Live Verify

- Scheduled task fires end-to-end.
- Skill retrieval/refinement path works with current feature flags.
- Prompt scanner gates scheduled tasks through the live API.
- PDDL/DSPy work is gated, not silently active.
- Plan skill behavior is verified in a real agent turn.

## Closeout Criteria

- Automation features are closed only with live task delivery and skill usage
  evidence, or moved to research with explicit status.
