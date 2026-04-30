---
title: Scheduler Skills Planning Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-30
feature_id: 015
migrated_from:
  - specs/execution/exec-scheduler.md
  - specs/execution/exec-scheduler2.md
  - specs/execution/exec-skills.md
  - docs/superpowers/findings/2026-04-23-adr-003-exec-14-dspy-gating.md
---

# Gate Ledger

## Scheduler Phase 1

Done static/build/unit gates:

- Go build/test/lint for scheduler paths.
- Python ruff/pytest for scheduler tools/subscriber.
- Alembic SQL dry-run through scheduler migrations.
- eight schedule tools registered.
- frontend typecheck/lint.
- adversarial verify PASS after timezone, cap bypass, ownership, ack race and
  hardcoded user findings were fixed.

Live gates still required:

- minute cron fires to Python subscriber.
- full agent turn completes.
- Matrix room receives result.
- `task_executions` row completes.
- chat UI creates a DB task.
- `/control/tasks` renders real DB data.

## Scheduler Phase 2

Phase 2 gates:

- dep digest posts package updates.
- email delivery reaches test inbox.
- Telegram delivery reaches test chat.
- `/metrics` exposes scheduler counters/histograms.
- inline edit changes next execution prompt.
- routine create/trigger with bearer works.
- GitHub signed webhook fires routine; invalid signature returns 403.
- condition task fires only above threshold.

## Skills

Done gates include DB schema/seed, finder, disabled-skill filter, mocked
refiner, coverage gate, iterative search, audit events, usage counters, offline
refiner, trigger-quality CLI, model-aware thresholds, skill extensions,
user-skill preferences, general/task-specific split and harness skill tracking.

Static gates additionally verified on 2026-04-25:

- Scheduler adapter/service-user tests pass.
- Plan skill loading/read-only planning tests pass.
- Skill Finder tests pass.
- Skill loader source modes and override order pass.
- Disabled-skill filtering removes disabled skills instead of falling back to
  all skills.
- `api_version`, skill type and assets are preserved by file parsing and DB
  row mapping shape.
- Prompt Scanner and Skills-Guard tests pass.

Static gates additionally verified on 2026-04-30:

- `agent.skills.usage_state` records provider-agnostic prompt usage, view count
  and pin state for filesystem skills.
- `format_skills_for_prompt_async` records prompt usage for actually rendered
  skills while preserving DB-backed `agent.agent_skills.usage_count`.
- `.skill` archive installs refuse pinned-skill overwrites and preserve the
  existing skill directory.
- Control skills read model exposes `usage`, `pinned` and `lifecycle_state`.
- Skill package parsing preserves small `.py`, `.go`, `.rs`, `.ts` and other
  text/code assets from arbitrary subfolders in the existing JSONB asset shape.
- Archive install security scan includes nonstandard code asset paths and
  blocks dangerous payloads before filesystem installation.

Remaining gates:

- live DB seed/source-mode roundtrip.
- real LLM refinement.
- real LLM iterative search.
- real LLM offline refinement.
- trigger-quality on production audit data.
- Pareto with >20 real usage events.
- empirical threshold tuning.
- Hindsight outcome feedback.
- promotion pipeline.
- live Control UI pin/unpin and GitHub import overwrite refusal.

## PDDL

No production gate exists yet. Before implementation:

- choose pilot workflow.
- define domain/problem representation.
- choose solver.
- define refusal/repair loop.
- define when PDDL is required vs skipped.

## DSPy

ADR-003 gates:

- G(-1).1 LLMSelector architecture match.
- G(-1).2 MIPROv2 PoC on one matrix flow.
- Phase-1 benchmark winner before D-2/D-3 schema/interface work.
- N-way A/B bucketing and artifact hash before live A/B variant.
