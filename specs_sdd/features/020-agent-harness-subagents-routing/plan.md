---
title: Agent Harness Subagents Routing Plan
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 020
---

# Plan

## Goal

Define and harden Matrix's agent harness shape beyond a single chat loop:
graphless runner, LangGraph runner, role routing, future subagents and
delegation policy. HermesAgent and other CLI agents are references for harness
principles, not product scope; Matrix remains focused on trading, geopolitics,
strategy, research and workflow assistance.

## Boundaries

- This feature does not build autonomous coding agents as a product feature.
- Subagents are future domain delegates, not hidden self-modifying workers.
- Control UI remains data/admin display unless a feature explicitly promotes a
  tool surface.
- Meta-Harness may evaluate routing/delegation behavior through traces, but
  production promotion requires explicit gates.

## First Order

1. Read HermesAgent and relevant `_ref` harness designs for graphless CLI-agent
   patterns: loop control, tool budgets, memory policy, subtask delegation,
   prompt layering and error recovery.
2. Map current Matrix runners: `dispatcher`, `langgraph`, `simple`.
3. Define when Matrix should use one agent, role switch, subagent, tool call or
   retrieval-only path.
4. Add Meta-Harness scenarios for routing and delegation invariants.
5. Implement only bounded hardening found by those scenarios.
