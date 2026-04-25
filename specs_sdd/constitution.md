---
title: Matrix SDD Constitution
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
adrs: []
---

# Matrix SDD Constitution

## Principles

1. Specs describe intent and current reality before code changes happen.
2. Feature folders are the unit of work; separate execution trees are legacy.
3. Every migrated Legacy source keeps provenance via `migrated_from`.
4. Implementation is not done until verify state is explicit.
5. UI, user-facing, networking, E2EE and agent-runtime work require live verify.
6. Research becomes binding only through `spec.md`, `plan.md`, `tasks.md`, or ADR.
7. Accepted ADRs require affected specs to be updated in the same migration step.

## Current State vs Target State

Each `features/NNN-*/spec.md` must contain:

- `Current State / Ist`
- `Target State / Soll`
- `Gap`
- `Out of Scope`
- `Acceptance Criteria`

`Current State` can mention partial, broken, obsolete or superseded work. It must
not be rewritten as if the target already exists.

## Execution Rules

- Use `tasks.md` for active work.
- Use `live-verify.md` for manual runtime proof.
- Use `closeout.md` when a feature is closed, including deviations from plan.
- Use `research.md` for websearch, paper notes, benchmark findings and tool
  comparisons.
- Use `adr/` only for decisions that should constrain future work.

## Legacy Rules During Migration

- Do not delete or rewrite `specs/` or `docs/superpowers/` during first pass.
- Do not move Superpowers files into `specs/execution/` unless explicitly chosen
  after the mapping pass.
- Prefer linking legacy sources from `MIGRATION_MAP.md` over duplicating whole
  files immediately.
- Mark unknown or ambiguous files as `triage_needed`, not as done.

