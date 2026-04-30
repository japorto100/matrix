---
title: Agent Harness Subagents Routing Gates
status: planned
owner: filip
created: 2026-04-27
updated: 2026-04-30
feature_id: 020
---

# Gates

- [x] HermesAgent v0.11 release research is summarized with transfer/non-
  transfer decisions.
- [ ] HermesAgent code deep-read is summarized with concrete Matrix diffs.
- [x] Route decisions are visible in audit artifacts before behavior changes.
- [x] SimpleLoop cannot bypass approval before tool execution.
- [x] Simple and LangGraph runners pass routing parity for no-tool scenarios.
- [x] Tool-budget and retry-loop failures become explicit gate failures.
  - 2026-04-30: provider-free routing-contract scenarios cover tool-budget
    exhaustion, provider retry loops and repeated failed tool calls as expected
    gate failures.
- [x] Runtime loop guards stop repeated same-tool failures before another model
  retry.
  - 2026-04-30: `agent.loop_guards.repeated_tool_failure_guard()` is used by
    both SimpleLoop and LangGraph increment routing and surfaces
    `tool_retry_guard_stopped` in degradation metadata.
- [x] Automatic memory flushes cannot race newer turns for the same thread.
  - 2026-04-30: runner scheduling assigns per-thread memory-sync generations;
    `_safe_sync_turn` serializes by thread and unit coverage proves stale
    generations do not call the MemoryManager.
- [x] Compressed historical context is not reinserted as bare user intent.
  - 2026-04-30: compressed summaries are wrapped as untrusted
    `context_summary` blocks and regex-detected injection text adds a security
    warning before the next LLM turn sees the summary.
- [x] Context-overflow recovery retries once after compression and resets retry
  state.
  - 2026-04-30: LangGraph and SimpleLoop classify context overflow via the
    provider-agnostic error classifier, compress messages, retry exactly once
    from iteration zero and surface `context_overflow_compress_retry`.
  - 2026-04-30: `routing-context-overflow-compress-retry-trace-shape` requires
    `llm.context_overflow_compress_retry` metadata and forbids raw prompt,
    message and summary payloads in runtime events.
- [ ] Subagent behavior remains out of production until search and holdout
  gates prove value.
  - 2026-04-30: domain delegate candidate metadata now records
    `delegation_decision=deferred` and `fallback_reason=subagents_disabled`;
    no production subagent execution is enabled.
  - 2026-04-30: remote A2A delegation is also runtime fail-closed unless
    `AGENT_A2A_MAX_SPAWN_DEPTH` explicitly allows the next hop. Static tests
    prove default depth zero does not instantiate the A2A client.
- [x] Enabled single-hop A2A uses fresh bounded child context, not inherited
  conversation/tool/memory state.
- [x] Runtime tool discovery is metadata-only and uses the current agent
  context tools.
  - 2026-04-30: `_prepare_system_prompt()` adds relevant tool hints only from
    `ctx.tools`, capped by progressive-disclosure level, and unit coverage
    asserts that hidden/high-disclosure schemas do not enter the prompt.
- [x] Tool hook policy is explicit before mutating or blocking tool behavior.
  - 2026-04-30: `tool_hook_policy` is default-off in graph state. When present,
    pre-tool veto emits a blocked runtime event and transformed tool results
    include `hook_policy` metadata before the result reaches audit, stream
    handoff or the next LLM turn.
  - 2026-04-30: `routing-tool-hook-policy-trace-shape` requires veto and
    transform hook metadata while forbidding raw output/secrets in runtime
    events; `run-tool-hook-policy-gate` passed 10/10.
- [x] Shell/output hooks cannot silently mutate backend tool output.
  - 2026-04-30: no shell hook runtime exists in the Python backend; Feature 020
    keeps it fail-closed until a future implementation adds explicit
    runtime-event/audit policy gates.

## 2026-04-30 Added Gates

- [x] Gated single-hop subagent execution is default-off/fail-closed.
  - 2026-04-30: default `AGENT_A2A_MAX_SPAWN_DEPTH=0` blocks A2A delegation
    before client creation and emits a blocked runtime event.
- [x] Child contexts are isolated by default; fork mode is explicit.
  - 2026-04-30: delegated A2A context carries role, parent thread id, depth,
    `memory_scope:explicit_context_only`, `context_mode:isolated` and bounded
    tool policy.
- [x] Child tool policy blocks recursive delegation, direct shared-memory
  writes, cross-platform sends and interactive approval deadlocks.
  - 2026-04-30: policy filters recursive delegation, memory write,
    schedule/send and code-exec tools; approval is non-interactive auto-deny.
- [x] Parent-side memory handoff records delegation outcomes.
  - 2026-04-30: completed child result emits a parent memory-handoff runtime
    event with digest and `child_memory_write_allowed=false`.
- [x] Subagent lifecycle emits Feature 033 runtime events.
  - 2026-04-30: accepted/started/completed/failed and timeout-as-stale are
    unit-tested through `a2a_delegate_node`.
  - 2026-04-30: node-level child-send timeout converts a hung child client into
    stale `subagent.delegation.timeout` metadata and closes the client.
