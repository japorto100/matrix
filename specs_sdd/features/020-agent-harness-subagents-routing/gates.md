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
- [ ] Subagent behavior remains out of production until search and holdout
  gates prove value.
  - 2026-04-30: domain delegate candidate metadata now records
    `delegation_decision=deferred` and `fallback_reason=subagents_disabled`;
    no production subagent execution is enabled.
