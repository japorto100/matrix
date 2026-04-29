---
title: Agent Harness Subagents Routing Tasks
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-29
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

- T010 [done-static] Define Matrix route taxonomy: direct answer, retrieval answer, tool use,
  role switch, subagent/delegate and human escalation.
- T011 [done-static] Define subagent contract for future domain delegates: input, allowed
  tools, memory scope, output schema, budget, audit events and cancellation.
- T012 [done-static] Define graphless runner parity requirements versus LangGraph.
- T013 [done-static] Define guardrails so subagents cannot silently write memory, KG claims or
  schedule tasks without explicit policy.
- T014 [done-static] Define role-routing interaction with current TradingRole prompts and
  memory recall tags.
- T015 [done-static] Define `max_spawn_depth` equivalent for Matrix delegates; default is
  zero/disabled, first allowed promotion is flat single-hop delegation.
- T016 [done-static] Define sibling coordination rules before any parallel delegate writes:
  artifact namespaces, memory write policy, KG proposal policy and tool budget.
- T017 [done-static] Define mid-run steering semantics as a future controlled operator/HITL
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
- T024 [done-static-live-smoke] Add trace assertions for runner variant, route
  decision and delegation decision.
  - 2026-04-27: `TraceExpectations` supports
    `required_route_decisions`, `required_runner_variants`,
    `required_delegation_decisions` and `max_spawn_depth`; runner-parity
    smoke requires `direct_answer`, `none` delegation and `spawn_depth=0`.
- T025 Add safety gates for reasoning leakage, resolved-secret persistence and
  provider-specific unsupported fields.
- T026 Add compression/thrashing gates: no infinite compression loop, retry
  counters reset after compression, no context poisoning.
- T027 Add hook-policy gates: pre-tool veto, transformed tool result and shell
  hook behavior must be explicit in audit traces before use.

## Implementation Candidates

- T030 [done-static] Add route-decision audit metadata before changing behavior.
  - 2026-04-27: `agent.routing.delegation_policy` centralizes the route
    metadata schema. `llm_node` now emits additive fields
    `route_taxonomy`, `delegate_kind`, `max_spawn_depth`, `allowed_tools`,
    `memory_scope`, `budget` and `fallback_reason` while preserving current
    behavior: `delegation_decision=none`, `spawn_depth=0`.
- T031 [done-static] Add bounded tool-budget telemetry visible to
  Meta-Harness.
  - 2026-04-27: `tool_node` now attaches non-secret budget metadata to
    `tool_call`/`tool_result` audit events: per-session tool calls, per-tool
    calls, token usage, iteration count and configured limits. Unit coverage
    verifies the metadata on a real tool execution without changing
    allow/deny behavior.
  - 2026-04-27: Meta-Harness trace gates can require those metadata keys via
    `required_event_metadata_keys`, so budget telemetry is enforceable in
    runner/delegation scenarios.
- T032 Add loop guard scenarios for repeated failed tool calls.
- T033 Add a future subagent API stub only after gates and contracts are clear.
- T034 Add transport abstraction candidate after Feature 011 review; avoid
  moving provider logic until Meta-Harness covers OpenRouter, mock, embeddings
  and local fallback paths.
- T035 [done-static] Add route-decision event schema before implementing domain delegates:
  `route_decision`, `delegation_decision`, `spawn_depth`, `delegate_kind`,
  `allowed_tools`, `memory_scope`, `budget`, `fallback_reason`.
- T036 [done-static] Implement route-decision telemetry as the first code
  slice; behavior may stay unchanged, but Meta-Harness must see why the runner
  chose no tool, retrieval, tool use, memory lookup or future delegation.
  - 2026-04-27: `llm_node` now emits a `route_decision` audit event for every
    LLM turn with runner, direct-answer/tool-use decision, tool names,
    memory/retrieval hints, `delegation_decision=none` and `spawn_depth=0`.
    Unit coverage verifies the memory-tool route metadata.
- T036a [done-live] Back runtime `agent.user_agent_settings` lookup with an
  Alembic-managed table so per-user agent settings no longer generate Postgres
  relation-missing errors during prompt preparation.
  - 2026-04-27: added revision `032_user_agent_settings`; live Postgres
    verification confirmed `agent.user_agent_settings` exists after
    `alembic upgrade head`.
- T037 Add Hermes-inspired but Matrix-specific loop guards: max tool retries,
  max provider retries, compression retry reset, stale async memory flush guard
  and unsupported-provider-field guard.
- [x] T037a Add graphless SimpleLoop approval parity: tool calls must pass
  `approval_node`, confirm-level tools fail closed without interrupt/resume, and
  tool-message emission must not duplicate `tool_node` output.

## Verification

- T040 [done-static] Static tests for route/delegation policy helpers.
- [x] T041 Meta-Harness runner parity with local lane for routing mechanics.
  2026-04-29 `llm-mock` run `run-simple-approval-parity-jsonl-20260429`
  passed `simple` and `langgraph` variants with no mismatches.
- T042 Live OpenRouter smoke for routing quality.
- T043 Holdout set before any behavioral promotion.
