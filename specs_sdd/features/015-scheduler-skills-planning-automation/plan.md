---
title: Scheduler, Skills, Formal Planning and Automation Plan
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
  - docs/superpowers/findings/2026-04-23-adr-003-exec-14-dspy-gating.md
adrs:
  - 0003
---

# Plan

## Architecture

This feature owns agent automation: scheduled task execution, skills discovery
and evolution, planning skill, PDDL validation and DSPy optimization gates.
`subfeatures.md` separates production automation from research tracks.

## Critical Files

- `python-backend/agent/scheduler/**`
- `python-backend/agent/skills/**`
- `python-backend/agent/tools/**schedule*`
- `python-backend/agent/security/prompt_scanner.py`
- `python-backend/agent/skills/global/plan/SKILL.md`
- `go-appservice/internal/scheduler/**`
- `frontend_merger/src/features/control/**Tasks*`
- `frontend_merger/src/features/control/**Skills*`
- `python-backend/experiments/skill_eval/**`

## Migration Strategy

1. Close out scheduler phase 1 separately from phase 2.
2. Split skills implemented pieces from feedback/promotion gaps.
3. Keep PDDL/DSPy gated until ADR-0003 and pilot gates are met.
4. Tie scheduled-task prompt security to Feature 013 where needed.
5. Keep notifications/media ingestion in research backlog unless promoted to a
   dedicated feature.

## Execution Order

1. Run remaining scheduler Phase-1 live gates.
2. Verify skills with real LLM paths.
3. Implement skill feedback/promotion only after outcome data exists.
4. Pick Scheduler Phase-2 slice by need; do not batch all infra jobs.
5. Keep PDDL/DSPy research gated until pilot/PoC exits are green.

## Risks

- Planning research being mistaken for production automation.
- Scheduler phase 1 marked closed without live delivery.
- Skill metrics based only on mocked LLM tests.
- DSPy schema work before algorithm winner is known.
