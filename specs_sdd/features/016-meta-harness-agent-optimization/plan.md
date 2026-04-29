---
title: Meta-Harness Agent Optimization Plan
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 016
---

# Plan

## Phase 0: Spec And Scope

Done by this feature creation:

- read the Meta-Harness paper.
- map existing Matrix code.
- separate 016 from 014 observability and 015 skills/scheduler.
- decide Python-only first.

## Phase 1: Scenario Runner

Build the smallest useful loop:

- scenario schema.
- 3-5 fixtures.
- direct Python Agent execution.
- artifact directory.
- raw trace and SSE capture.
- deterministic trace gates.

No frontend and no Go.

## Phase 2: Tool And Memory Coverage

Expand scenario classes:

- memory automatic recall/retain.
- explicit memory tools.
- non-destructive registered tools.
- consent-required tools with dry/local guards.
- sandbox/file/browser where available.
- scheduler tool DB behavior without Matrix delivery.

## Phase 3: Proposer Upgrade

Move from truncated context prompt to filesystem-backed candidate history:

- source/config snapshots.
- candidate traces.
- scores/verdicts.
- rejected-candidate reasons.
- bounded patch/config overlay output.

## Phase 4: Promotion

Add real keep/discard discipline:

- search vs holdout split.
- Pareto frontier.
- safety/tool/memory gates.
- cost/latency thresholds.
- promotion command.

## Phase 5: MCP And Product Live Verify

Expose stable commands to MCP and then verify product path:

- `/mcp-traces` wrapper.
- Go Gateway/Frontend path as live verify, not core loop.
- Control UI dashboard later.

## Risk Controls

- never promote from search set only.
- never let proposer see holdout scores.
- never run destructive tools in eval without explicit sandboxed scenario.
- keep evaluator fixtures immutable during a run.
- store every rejected candidate with rationale.
