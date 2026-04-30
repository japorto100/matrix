---
title: Agent Harness Subagents Routing Tasks
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-30
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
- [x] T018 [done-static] Define provider transport boundary for Matrix: OpenAI-compatible,
  Responses-style, OpenRouter/LiteLLM, embeddings and rerankers.
  - 2026-04-29: ADR-0009 fixes the current boundary for this phase:
    provider-specific SDKs remain references; runtime/harness gates use
    provider-agnostic LiteLLM-compatible metadata and explicit fake-provider
    opt-in.

## Meta-Harness Gates

- [x] T020 [done-static] Add routing scenarios where the correct behavior is no
  tool and no subagent.
  - 2026-04-30: provider-free `routing-contract` Meta-Harness lane includes
    `routing-no-tool-no-subagent` with `direct_answer`, `delegation_decision=none`
    and `spawn_depth=0`.
- [x] T021 [done-static] Add routing scenarios where retrieval should beat
  subagent delegation.
  - 2026-04-30: `routing-retrieval-beats-delegation` asserts
    `route_taxonomy=retrieval_answer`, no delegation and explicit budget
    metadata.
- [x] T022 [done-static] Add routing scenarios where a domain delegate would be
  justified, but is currently expected to defer because subagents are not
  implemented.
  - 2026-04-30: `build_delegation_defer_metadata()` and
    `routing-domain-delegate-deferred` record `delegation_decision=deferred`,
    `delegate_kind=domain`, `fallback_reason=subagents_disabled` and
    `spawn_depth=0`.
- [x] T023 [done-static] Add failure scenarios for tool budget exhaustion,
  retry loops and provider errors.
  - 2026-04-30: `routing-tool-budget-exhaustion-fails` and
    `routing-provider-retry-loop-fails` assert deterministic gate failures
    without provider calls.
- T024 [done-static-live-smoke] Add trace assertions for runner variant, route
  decision and delegation decision.
  - 2026-04-27: `TraceExpectations` supports
    `required_route_decisions`, `required_runner_variants`,
    `required_delegation_decisions` and `max_spawn_depth`; runner-parity
    smoke requires `direct_answer`, `none` delegation and `spawn_depth=0`.
- [x] T025 [done-static] Add safety gates for reasoning leakage,
  resolved-secret persistence and provider-specific unsupported fields.
  - 2026-04-29: runtime now omits `tools` and `reasoning_effort` only when
    LiteLLM-derived metadata explicitly marks the model as incompatible; unknown
    custom/provider models retain previous behavior.
  - 2026-04-30: `TraceExpectations.forbidden_event_metadata_keys` gates
    provider-specific metadata and resolved secrets in trace artifacts;
    `routing-forbidden-provider-secret-metadata-fails` proves the failure path.
- [x] T026 Add compression/thrashing gates: no infinite compression loop, retry
  counters reset after compression, no context poisoning.
  - 2026-04-30: repeated same-tool failures are now runtime-stopped in both
    SimpleLoop and LangGraph via `agent.loop_guards`, preventing tool/LLM
    thrash before max-iteration exhaustion. Compression reset and context
    poisoning gates remain open.
- [x] T027 Add hook-policy gates: pre-tool veto, transformed tool result and shell
  hook behavior must be explicit in audit traces before use.
  - 2026-04-30: LangGraph `tool_node` now accepts an explicit per-turn
    `tool_hook_policy`. Missing policy is fail-open/unchanged; configured
    `pre_tool_veto`/`deny_tools` blocks execution with a blocked runtime event,
    and configured result-key redaction transforms tool output before audit,
    stream handoff and the next LLM turn. Unit coverage proves veto, transform
    and graph-state policy propagation.
  - 2026-04-30: Shell/output hooks remain intentionally unsupported in the
    Python backend. Any future shell hook must first add the same explicit
    audit/runtime-event policy surface before it can be used.
  - 2026-04-30: `meta_harness routing-contract` now includes
    `routing-tool-hook-policy-trace-shape`; `run-tool-hook-policy-gate` passed
    10/10 provider-free scenarios.

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
- [x] T032 [done-static] Add loop guard scenarios for repeated failed tool
  calls.
  - 2026-04-30: `TraceExpectations.max_repeated_tool_failures_per_tool` and
    `routing-repeated-failed-tool-calls-fails` make repeated tool failures an
    explicit gate failure.
- [x] T033 Add a future subagent API stub only after gates and contracts are clear.
  - 2026-04-30: runtime remains fail-closed by default:
    `agent.graph.nodes.a2a_node` refuses remote A2A delegation unless
    `AGENT_A2A_MAX_SPAWN_DEPTH` explicitly permits the next depth. When enabled,
    the child receives a fresh bounded context containing role, parent thread,
    spawn depth and explicit-context-only memory scope.
- T034 Add transport abstraction candidate after Feature 011 review; avoid
  moving provider logic until Meta-Harness covers OpenRouter, mock, embeddings
  and local fallback paths.
  - 2026-04-29: first coverage slice added via `provider-smoke`; full transport
    abstraction remains deferred because GitNexus marks the shared client path
    as CRITICAL impact.
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
  - 2026-04-29: unsupported-provider-field guard implemented for known model
    capability metadata in `llm_node`; broader retry/thrashing guards remain
    open.
  - 2026-04-30: static Meta-Harness gates now cover repeated tool failures,
    provider retry loops and forbidden provider/secret metadata. Compression
    reset and stale async memory flush guards remain open under Feature 012/016.
  - 2026-04-30: runtime now stops after
    `AGENT_MAX_TOOL_FAILURES_PER_TOOL` repeated failures for the same tool in
    SimpleLoop and LangGraph, emits `tool_retry_guard_stopped`, and returns a
    bounded final response instead of asking the model for another identical
    tool retry.
  - 2026-04-30: stale async memory flush guard is now implemented in the
    runner scheduling path: automatic post-answer sync uses per-thread
    generations and skips stale generations before MemoryManager writes.
    Compression retry reset and deeper context-poisoning checks remain open.
  - 2026-04-30: compressed context summaries are now explicitly untrusted and
    injection-pattern marked before reinsertion. Compression retry reset remains
    open; context-poisoning has a first static guard under Feature 012.
  - 2026-04-30: context-overflow recovery now performs exactly one
    compress-and-retry in both LangGraph and SimpleLoop, resets the retry state
    to iteration zero for the compressed message set, and emits
    `context_overflow_compress_retry` degradation/runtime metadata. This closes
    the compression retry reset slice; broader provider fallback loops remain
    Feature 011 work.
  - 2026-04-30: `routing-context-overflow-compress-retry-trace-shape` now gates
    the recovery runtime event shape and forbids raw messages/prompts/summaries
    from leaking into runtime metadata.
- [x] T037a Add graphless SimpleLoop approval parity: tool calls must pass
  `approval_node`, confirm-level tools fail closed without interrupt/resume, and
  tool-message emission must not duplicate `tool_node` output.
- [x] T038 [done-static] Move progressive tool discovery into the actual
  runtime prompt path, not only Control.
  - 2026-04-30: `_prepare_system_prompt()` now injects query-gated
    metadata-only `Tool Discovery Hints` from the current `ctx.tools` via
    `agent.tools.catalog.search_tool_catalog()`. The block includes name,
    group, risk, approval and summary only; full input schemas still flow only
    through the normal provider tool-calling payload.

## Verification

- T040 [done-static] Static tests for route/delegation policy helpers.
  - 2026-04-30: added A2A node tests for default fail-closed spawn depth and
    fresh bounded child context when single-hop delegation is enabled.
- [x] T041 Meta-Harness runner parity with local lane for routing mechanics.
  2026-04-29 `llm-mock` run `run-simple-approval-parity-jsonl-20260429`
  passed `simple` and `langgraph` variants with no mismatches.
- T042 Live OpenRouter smoke for routing quality.
- T043 Holdout set before any behavioral promotion.
- [x] T044 [done-static-live-smoke] Run provider-free routing contract
  Meta-Harness lane.
  - 2026-04-30:
    `uv run python -m meta_harness.meta_cli routing-contract --run-id run-routing-contract-20260430 --data-dir /tmp/matrix-meta-harness-routing-contract`
    passed 7/7 scenarios and wrote `routing_contract.json`.

## 2026-04-30 Gated Single-Hop Subagent Additions

- [x] T045 Define provider-agnostic `delegate_task`/subagent execution interface
  using isolated context by default and explicit fork mode only when requested.
  - 2026-04-30: `build_single_hop_delegation_policy()` defines the
    provider-agnostic policy envelope for role, depth, context mode,
    concurrency cap and child tool policy. Current A2A execution uses isolated
    explicit-context mode.
- [x] T046 Implement single-hop gated execution default-off/fail-closed, with
  depth and concurrency policy.
  - 2026-04-30: `a2a_delegate_node` remains default-off via
    `AGENT_A2A_MAX_SPAWN_DEPTH=0`; static tests prove no client is created in
    the default path and single-hop routing only starts when depth permits it.
- [x] T047 Enforce child tool policy: no recursive delegation, no direct shared
  memory writes, no cross-platform send, no interactive approval deadlocks.
  - 2026-04-30: child policy blocks `delegate_task`, A2A wait/delegate tools,
    memory writes, scheduler/send-message and code/sandbox execution by
    default; approval mode is `non_interactive_auto_deny`.
  - 2026-04-30: A2A child requests now parse Matrix-owned delegation context
    into runtime policy, filter the actual tool registry to `allowed_tools` and
    propagate `memory_write_policy=parent_only` into both LangGraph and
    SimpleLoop state. `memory_retain_node` blocks these child turns before
    touching the durable Memory engine.
- [x] T048 Emit Feature 033 lifecycle events for accepted, started, tool activity,
  completed, error, timeout, killed and stale states.
  - 2026-04-30: A2A node emits `subagent.delegation.accepted`,
    `started`, `completed`, `failed` and timeout-as-`stale` runtime events.
    Kill/pause remain future Control operations.
  - 2026-04-30: the same lifecycle events are persisted into audit metadata so
    Feature 029 can reconstruct subagent run rows in Ops replay, not only from
    transient graph state.
  - 2026-04-30: `a2a_delegate_node` now wraps child sends with
    `AGENT_A2A_DELEGATION_TIMEOUT_SECONDS`; even a blocking/faulty client is
    converted into a stale `subagent.delegation.timeout` runtime event and the
    child client is closed.
  - 2026-04-30: Ops replay now treats completion, stale timeout and parent
    memory handoff as one correlated run by `child_task_id`, exposing terminal
    reason and outcome while durable kill/pause remain future work.
- [x] T049 Add parent-side memory handoff event for delegation outcomes.
  - 2026-04-30: completed child results emit
    `subagent.parent_memory_handoff` as a parent-only memory event with result
    digest; child memory writes stay disabled.
  - 2026-04-30: the handoff is now consumed by the Ops read model as
    parent-curation metadata, so the downstream operator view can verify that
    child output was made available to the parent without permitting a child
    memory write.
- [x] T050 [done-static] Ensure A2A context is policy, not prompt-only text.
  - 2026-04-30: `/api/v1/agent/chat` recognizes only Matrix A2A child
    threads (`a2a-*`) with the Matrix delegation prefix, converts role/depth/
    parent-thread/tool/memory fields into `AgentExecutionContext`, and leaves
    ordinary user `context` text non-authoritative.
