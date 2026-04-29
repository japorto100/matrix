---
title: Meta-Harness Agent Optimization Subfeatures
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 016
---

# Subfeatures

## 016.1 Scenario Runner

Status: planned.

Owns multi-turn simulated user execution against the Python Agent. It must
support service mode and in-process mode, shared scenario fixtures, per-turn
headers/user ids and artifact capture.

## 016.2 Tool-Aware Evaluation

Status: planned.

Owns real ToolRegistry use during evals, tool allow/deny expectations, consent
trace assertions, sandbox/file/browser/scheduler/A2UI cases and canonical tool
name mapping.

## 016.3 Memory-Aware Evaluation

Status: planned, next implementation focus.

Owns pre-seeded memory fixtures, automatic memory prefetch/retain assertions,
explicit memory tool tests and Hindsight/MemPalace/Fusion route visibility.

This subfeature treats Matrix memory as a mixed system, not one interchangeable
store:

- Hindsight mode: normalized summaries, durable facts, user preferences and
  correction semantics.
- MemPalace mode: verbatim/episodic evidence, loci metadata and query
  sanitization.
- Fusion mode: both routes active, with route/provider metadata and conflict
  rules that let source-backed verbatim evidence constrain stale summaries.

The Meta-Harness must include search-set scenarios for improving this behavior
and a protected holdout set for regressions. Existing
`experiments/memory_eval` A/B scripts remain source evidence and can feed
fixtures, but the agent-level pass/fail signal belongs in the `meta_harness`
scenario runner.

## 016.4 Candidate Artifact Store

Status: planned.

Owns the filesystem run layout: candidate code/config snapshots, raw traces,
SSE transcripts, scores, verdicts, patches and proposer notes.

## 016.5 Proposer Interface

Status: partial via Feature 014.

Extends the current proposer from truncated summaries to paper-like full-history
inspection. The proposer may be Codex as coding agent, the local LiteLLM
proposer, or both.

## 016.6 Scoring And Judging

Status: partial via Feature 014.

Combines deterministic trace gates, existing composite fitness, task-specific
rubrics and optional LLM-as-judge. Scores must remain auditable and separable by
search set vs holdout set.

## 016.7 CLI And MCP Surface

Status: partial via `agent.mcp_traces`.

Provides stable commands/tools:

- `run-scenario`
- `evaluate`
- `propose`
- `loop`
- `history`
- `show-trace`
- `pareto`
- `promote`

CLI is the first stable interface; MCP wraps it once artifacts and schemas are
settled.

## 016.8 Skill Evolution Bridge

Status: defer until base loop is stable.

Maps EvoSkill-style failure clustering and skill candidate promotion onto
Matrix skills. This belongs after scenario runner, trace gates and candidate
store exist.

## 016.9 Autoresearch Discipline

Status: adopted as process pattern.

Uses fixed evaluator, fixed budget, result log, keep/discard semantics and
branch/patch rollback discipline. It is not a separate runtime product.
