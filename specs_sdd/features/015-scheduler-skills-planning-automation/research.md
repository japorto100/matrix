---
title: Scheduler Skills Planning Research
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-30
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
- general skills are broad but should still be query-gated by default; always
  loading `memory-usage` caused trivial/no-tool turns to over-inject skills and
  inflate prompt tokens. `AGENT_SKILL_ALWAYS_LOAD_GENERAL=1` remains an escape
  hatch.
- stopword/instruction-token filtering before BM25 so words like "reply",
  "short", "sentence", "with" do not trigger unrelated Matrix domain skills.

Open:

- real production audit data for trigger-quality.
- skill compliance rate, not just load rate.
- promotion from repeated successful refinements.
- SkillRL/EBM/MemRL only after enough sessions and skill pool size.

## Hermes Agent Skill Lifecycle Follow-Up 2026-04-30

Derived from the fresh `_ref/hermes-agent` pull and cross-checked against the
agent-skills/procedural-memory direction from the SOTA review.

Reusable for Matrix:

- background skill maintenance should be grounded in usage evidence, not just
  static skill files.
- pinned or curated skills need an explicit write fence so automated import,
  archive install or future skill-evolution jobs cannot overwrite them
  silently.
- usage metadata must cover filesystem, team and personal skills, not only
  DB-backed `agent.agent_skills` rows.
- lifecycle state should be visible in Control because promotion/archive
  decisions need operator context.

Implemented Matrix-local version:

- provider-agnostic sidecar `agent.skills.usage_state` for prompt usage, view
  count, pin state and active lifecycle metadata.
- import/archive pinned-skill overwrite refusal.
- Control skills read model exposes usage and lifecycle state.
- package asset parsing now keeps small text/code assets from arbitrary
  subfolders in the existing `assets JSONB` shape and includes them in the
  install-time security scan. This fixes the gap where `src/*.py`, `go/*.go`
  or `crates/*.rs` could remain filesystem-only and under-scanned.

Current storage rule:

- `SKILL.md` body is stored as `agent.agent_skills.content`.
- structured metadata uses normal columns.
- small text/code package assets use `agent.agent_skills.assets JSONB`.
- large/binary assets should become artifact-store references with manifest
  metadata, not inline JSONB.

Not copied from Hermes:

- CLI-specific curator flow, TUI affordances and coding-agent assumptions.
- provider-specific telemetry or prompt formats.

Related fresh inputs:

- `Z_Additional_For_Tool_Stuff.md` for normal/tool/MCP boundary pressure.
- Feature 016 `research.md` domain-contract notes for the rule that Meta-
  Harness evaluates agent-runtime candidates after the real runtime module is
  changed.

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
