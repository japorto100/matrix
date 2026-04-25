---
title: Scheduler Skills Planning Research
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 015
migrated_from:
  - specs/execution/exec-skills.md
  - specs/execution/exec-14-pddl-formal-planning.md
  - specs/execution/exec-14-DSPy.md
  - docs/superpowers/findings/2026-04-23-adr-003-exec-14-dspy-gating.md
---

# Research

## Skills

Adopted:

- retrieval before prompt injection.
- query-specific refinement.
- coverage gate before refinement.
- iterative search when top-k is weak.
- offline refinement as preprocessing.
- general always-load vs task-specific retrieval split.

Open:

- real production audit data for trigger-quality.
- skill compliance rate, not just load rate.
- promotion from repeated successful refinements.
- SkillRL/EBM/MemRL only after enough sessions and skill pool size.

## PDDL

PDDL is for hard constraints, deadlines, resource budgets and multi-step
workflow validity. It does not replace JSON schemas, OpenAPI, MCP or normal
tool calling.

Default adoption path:

- write/choose a small pilot domain.
- LLM formalizes intent/problem.
- formal solver validates.
- invalid plans are repaired/refused before execution.

Do not adopt:

- PDDL for trivial CRUD.
- low-latency trading execution.
- solver path without explicit fallback/refusal behavior.

## DSPy

ADR-003 reframes DSPy as additive prompt-content optimization. It should not
replace skill lifecycle logic such as trigger quality, promotion/eviction or
Pareto counters.

Gates:

- LLMSelector architectural match check first.
- one cheap PoC on matrix data before reading/implementation week.
- defer schema/interface until winner selection.
- A/B needs N-way bucketing and compiled artifact hash.

## Scheduler

River/Postgres is the Phase-1 pragmatic scheduler. Temporal remains a later
option for long-running workflows that need saga, compensation, replay or human
approval. Do not introduce Temporal for cron-like tasks.
