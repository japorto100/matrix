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
