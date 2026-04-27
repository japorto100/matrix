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
- T001a [done-research] Update `_ref/hermes-agent` to upstream
  `v2026.4.23-600-g8ed599dc` and read `RELEASE_v0.11.0.md` for immediate
  harness lessons: transport layer, orchestrator subagents, `max_spawn_depth`,
  sibling coordination, plugin hooks, shell hooks, `/steer`, compression
  hardening, memory metadata and provider/credential safety.
- T002 Compare HermesAgent principles with Matrix `simple`, `dispatcher` and
  `langgraph` runners.
- T003 Record which HermesAgent ideas transfer to Matrix and which are
  coding-agent-specific and out of scope.
- T004 Review additional `_ref` agent harnesses only for bounded patterns:
  tool budget, retry, role handoff, context staging and failure recovery.
- T005 Deep-read HermesAgent files after the release-note pass:
  `run_agent.py`, `agent/transports/*`, `agent/context_compressor.py`,
  `agent/memory_manager.py`, `agent/memory_provider.py`,
  `agent/credential_pool.py`, `model_tools.py`, `gateway/session.py` and
  `skills/software-development/subagent-driven-development/SKILL.md`.
- T006 Capture specific Matrix diffs after deep-read: what to implement in
  Feature 011/012/013/015/016/020 and what to reject as CLI-coding-agent-only.

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
- T015 Define `max_spawn_depth` equivalent for Matrix delegates; default is
  zero/disabled, first allowed promotion is flat single-hop delegation.
- T016 Define sibling coordination rules before any parallel delegate writes:
  artifact namespaces, memory write policy, KG proposal policy and tool budget.
- T017 Define mid-run steering semantics as a future controlled operator/HITL
  capability, not as an unlogged prompt mutation.
- T018 Define provider transport boundary for Matrix: OpenAI-compatible,
  Responses-style, OpenRouter/LiteLLM, embeddings and rerankers.

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
- T025 Add safety gates for reasoning leakage, resolved-secret persistence and
  provider-specific unsupported fields.
- T026 Add compression/thrashing gates: no infinite compression loop, retry
  counters reset after compression, no context poisoning.
- T027 Add hook-policy gates: pre-tool veto, transformed tool result and shell
  hook behavior must be explicit in audit traces before use.

## Implementation Candidates

- T030 Add route-decision audit metadata before changing behavior.
- T031 Add bounded tool-budget telemetry visible to Meta-Harness.
- T032 Add loop guard scenarios for repeated failed tool calls.
- T033 Add a future subagent API stub only after gates and contracts are clear.
- T034 Add transport abstraction candidate after Feature 011 review; avoid
  moving provider logic until Meta-Harness covers OpenRouter, mock, embeddings
  and local fallback paths.
- T035 Add route-decision event schema before implementing domain delegates:
  `route_decision`, `delegation_decision`, `spawn_depth`, `delegate_kind`,
  `allowed_tools`, `memory_scope`, `budget`, `fallback_reason`.

## Verification

- T040 Static tests for route/delegation policy helpers.
- T041 Meta-Harness runner parity with local lane for routing mechanics.
- T042 Live OpenRouter smoke for routing quality.
- T043 Holdout set before any behavioral promotion.
