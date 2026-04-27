---
title: Agent Harness Subagents Routing Tasks
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 020
---

# Tasks

## Research / Reference

- T001 Read `_ref/hermes-agent` harness loop, memory, tool and self-learning
  code with attention to graphless operation.
- T002 Compare HermesAgent principles with Matrix `simple`, `dispatcher` and
  `langgraph` runners.
- T003 Record which HermesAgent ideas transfer to Matrix and which are
  coding-agent-specific and out of scope.
- T004 Review additional `_ref` agent harnesses only for bounded patterns:
  tool budget, retry, role handoff, context staging and failure recovery.

## Architecture

- T010 Define Matrix route taxonomy: direct answer, retrieval answer, tool use,
  role switch, subagent/delegate and human escalation.
- T011 Define subagent contract for future domain delegates: input, allowed
  tools, memory scope, output schema, budget, audit events and cancellation.
- T012 Define graphless runner parity requirements versus LangGraph.
- T013 Define guardrails so subagents cannot silently write memory, KG claims or
  schedule tasks without explicit policy.
- T014 Define role-routing interaction with current TradingRole prompts and
  memory recall tags.

## Meta-Harness Gates

- T020 Add routing scenarios where the correct behavior is no tool and no
  subagent.
- T021 Add routing scenarios where retrieval should beat subagent delegation.
- T022 Add routing scenarios where a domain delegate would be justified, but is
  currently expected to defer because subagents are not implemented.
- T023 Add failure scenarios for tool budget exhaustion, retry loops and
  provider errors.
- T024 Add trace assertions for runner variant, route decision and delegation
  decision.

## Implementation Candidates

- T030 Add route-decision audit metadata before changing behavior.
- T031 Add bounded tool-budget telemetry visible to Meta-Harness.
- T032 Add loop guard scenarios for repeated failed tool calls.
- T033 Add a future subagent API stub only after gates and contracts are clear.

## Verification

- T040 Static tests for route/delegation policy helpers.
- T041 Meta-Harness runner parity with local lane for routing mechanics.
- T042 Live OpenRouter smoke for routing quality.
- T043 Holdout set before any behavioral promotion.
