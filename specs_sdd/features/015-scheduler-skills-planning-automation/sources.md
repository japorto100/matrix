---
title: Scheduler Skills Planning Sources
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 015
---

# Sources

## Main Docs

| Source | Role in SDD |
|---|---|
| `main_docs/root/AGENT_RUNTIME_ARCHITECTURE.md` | Runtime roles, policy tiers, memory-write policy and Temporal-later context referenced by scheduler specs. |
| `main_docs/root/AGENT_ARCHITECTURE.md` | Agent orchestration defaults and tool/registry principles. |
| `main_docs/root/AGENT_TOOLS.md` | Tool/language classification and PDDL/tool boundary context. |
| `main_docs/specs/EXECUTION_PLAN.md` | Historical phase-board input only; current source of truth is SDD tasks/gates. |

## Execution / ADR Sources

| Source | Role in SDD |
|---|---|
| `specs/execution/exec-scheduler.md` | Scheduler architecture and River/Postgres plan. |
| `specs/execution/exec-scheduler2.md` | Ratified scheduler decisions. |
| `specs/execution/exec-skills.md` | Skills runtime, import, finder/refiner/store and gates. |
| `specs/execution/exec-14-pddl-formal-planning.md` | Formal planning/PDDL plan. |
| `specs/execution/exec-14-DSPy.md` | DSPy research/gating plan. |
| `docs/superpowers/findings/2026-04-23-adr-003-exec-14-dspy-gating.md` | Benchmark-first DSPy decision and reading-priority correction. |

## Paper / Research Sources

Paper corpus stays research-gated. DSPy/PDDL/skills papers should not trigger
implementation until the relevant PoC/live gates pass.
