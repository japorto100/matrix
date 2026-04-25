---
title: Scheduler Skills Planning Subfeatures
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 015
---

# Subfeatures

## 015.1 Scheduler Phase 1

Status: built, live verify required.

Scope:

- River/Postgres scheduler in Go appservice.
- `scheduler.scheduled_tasks` and `scheduler.task_executions`.
- JetStream/NATS dispatch to Python subscriber.
- eight `schedule_*` agent tools.
- `/control/tasks` list/actions UI.
- Matrix-only delivery.
- prompt scanner, ownership checks, hard cap and per-turn rate limit.

Open:

- live cron tick -> agent turn -> Matrix delivery.
- live chat-to-DB via Agent Chat UI.
- live `/control/tasks` against real DB.

## 015.2 Scheduler Phase 2

Status: planned, ready after decisions.

Scope:

- dep-update matrix digest.
- email and Telegram delivery.
- Prometheus scheduler metrics.
- Control-UI inline edit.
- dev/admin routines with signed webhook secret.
- GitHub PR webhook routines.
- condition-triggered tasks.
- remaining infra jobs: SeaweedFS tiering, key rotation, cert renewal,
  harness eval, user digest.

Open:

- resolve/confirm D-1..D-8 before coding.
- keep Temporal as Phase-3 option, not committed.

## 015.3 Skills Runtime

Status: mostly built.

Scope:

- 3-tier loader and `filesystem|db|hybrid`.
- DB skill seed and `agent_skills`.
- BM25/dense/RRF finder.
- query-specific refiner.
- coverage gate.
- iterative search.
- offline refiner.
- general/task-specific split.
- `user_skill_preferences` cutover.
- `api_version`, assets and usage counters.

Open:

- real LLM verify for refinement, iterative search and offline refinement.
- full runtime/UI migration from legacy skill state.
- empirical tuning of model-aware thresholds.

## 015.4 Skill Feedback And Promotion

Status: partial.

Scope:

- skill audit events.
- trigger-quality CLI.
- Pareto frontier helper.
- harness scorer tracks loaded skills/events.

Open:

- Hindsight/outcome feedback.
- skill compliance judge.
- promotion pipeline from repeated successful refinements.
- Pareto with enough real usage events.
- skill eval variants: baseline, compose, offline-only, offline+compose.

## 015.5 Plan Skill

Status: built, live verify required.

Scope:

- global `plan` skill.
- domain-agnostic read-only planning mode.
- DE/EN trigger descriptions.
- seven-section plan template.
- user confirmation before execution.

Open:

- live chat smoke that planning does not execute side effects.

## 015.6 PDDL Formal Planning

Status: gated research/planned.

Scope:

- PDDL 2.1 as initial language candidate.
- LLM as formalizer, solver as validator.
- suitable for high-risk workflows with hard constraints.
- potential MCP interface for PDDL operations.
- Saga/compensation as during-execution complement, not PDDL replacement.

Open:

- choose pilot workflow.
- choose solver stack.
- build NL->problem formalization path.
- keep out of low-latency/trivial CRUD paths.

## 015.7 DSPy / Prompt Optimization

Status: ADR-003 gated.

Scope:

- DSPy/GEPA/TextGrad/LLMSelector/p1 evaluation.
- add prompt-content optimization alongside skill lifecycle, not replace it.
- potential optimizer for smart routing, skills and NL->PDDL translator.

Open:

- G(-1).1 LLMSelector architectural match.
- G(-1).2 MIPROv2 PoC benchmark.
- no DB schema or standard module interface until algorithm winner is known.
- N-way A/B bucketing and artifact hash before A/B rollout.
