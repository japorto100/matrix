---
title: Real Meta-Harness Outer Loop
status: planned
owner: filip
created: 2026-05-01
updated: 2026-05-01
feature_id: 034
---

# Real Meta-Harness Outer Loop

## Intent

Matrix must stop treating static contract lanes as if they were the full
Meta-Harness method. This feature owns the real paper-style iteration loop:
a proposer inspects prior candidate source, scores and raw traces, proposes
bounded harness changes, a frozen evaluator scores them on a search set, and
the next iteration uses the accumulated filesystem experience.

Feature 016 remains the agent harness and artifact infrastructure owner.
Feature 023 remains the inner-loop/AutoResearch owner for bounded sweeps such
as RAG, extraction, memory/context and tool-policy candidates. Feature 034 owns
the executable outer-loop discipline that uses those artifacts repeatedly.

## Scope

- Paper-aligned Matrix domain contract for iterative runs.
- Search-set and hidden-holdout split for agent-harness improvement.
- Proposer workspace over candidate source snapshots, scores, verdicts, SSE and
  raw trace JSON.
- Frozen evaluator and no self-certification promotion rule.
- Bounded write scopes for runtime candidates.
- Keep/discard/defer ledger and Pareto frontier across iterations.
- AutoResearch-style run discipline: fixed evaluator, fixed budget, explicit
  mutable zone, rollback/discard on regression.
- Inner-loop bridge from Feature 023 into outer-loop candidate promotion.

## Non-Goals

- Renaming every existing provider-free contract lane to Meta-Harness.
- Letting proposer notes certify success.
- Mutating evaluator, goldens or holdout data during a run.
- Provider-specific optimization assumptions.
- Browser live verification in the first iteration.

## Success Definition

The feature is useful only when a run can show at least one complete loop:

1. baseline candidate evaluated on search scenarios;
2. proposer reads raw prior artifacts;
3. bounded candidate is produced with source/config snapshot;
4. frozen evaluator scores it;
5. decision is logged as keep, discard or defer;
6. Pareto/frontier changes are visible;
7. holdout remains hidden until explicit promotion check.

Static gates can support this, but they do not count as a completed
Meta-Harness iteration by themselves.

## Trace Source Rule

Frontend interaction is not required for the first real loop. Feature 034 may
use synthetic scenario/user turns as long as they execute the real Python agent
runtime and write real trace, SSE, score and verdict artifacts. Browser and
frontend usage is a later downstream live gate for rendering and interaction,
not the source of truth for initial harness optimization.
