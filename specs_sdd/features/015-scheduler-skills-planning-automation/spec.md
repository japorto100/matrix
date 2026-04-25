---
title: Scheduler, Skills, Formal Planning and Automation
status: mixed_active
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
- PDDL is scoped but not an active implementation default.
- DSPy requires ADR-003 gates before broader work.

## Verify

- [ ] Scheduled task fires end-to-end.
- [ ] Skill retrieval/refinement path works with current feature flags.
- [ ] Prompt scanner gates scheduled tasks.
- [ ] PDDL/DSPy work is gated, not silently active.
- [ ] Plan skill behaves as read-only planning with confirmation gate.

## Closeout Criteria

- Automation features are closed only with live task delivery and skill usage
  evidence, or moved to research with explicit status.
