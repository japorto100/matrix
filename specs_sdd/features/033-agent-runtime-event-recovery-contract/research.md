---
title: Agent Runtime Event Recovery Research
status: draft
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 033
---

# Research

## Local References

- `_ref/hermes-agent/tools/delegate_tool.py`: subagent start/thinking/tool
  events, parallel children, interrupt-aware polling, parent-side memory
  observation and non-interactive dangerous command denial.
- `_ref/claude_code/openclaw/src/agents/subagent-*`: subagent registry,
  liveness, stale recovery, lifecycle ended reasons, thread binding and
  completion announcement.
- `_ref/claude_code/openclaude/src/coordinator/workerAgent.ts`: simple
  role-based worker definitions for coordinator mode.

## Findings

- Subagents need isolated sessions by default, explicit fork mode only when
  requested and a depth/concurrency policy.
- Children should not write directly to shared memory. Parent memory curation
  is safer and auditable.
- Runtime events need stable identities so downstream UI can render tool calls,
  artifacts and subagent state without parsing assistant text.
- Stale child detection, timeout, kill and completion outcomes must be explicit
  events, not inferred from missing output.

## 2026-04-30 Ops Surface Transfer

Agent Chat already consumes runtime events from stream metadata. Control/Ops now
uses the same envelope by reading `runtime_events` from audit metadata and
rendering kind/status lanes. This confirms the contract can serve both
downstream chat UX and operator read models without provider-specific fields.

The next reliability step is not a bigger UI. It is ensuring every producer that
currently returns runtime events in graph/API state also persists a redacted
event reference for replay: memory retain/recall, RAG retrieval, KG claim
selection, tool execution and subagent lifecycle.

2026-04-30 implementation update: LLM, tool execution, memory recall/retain and
scoped RAG/KG retrieval now persist runtime-event envelopes into audit metadata.
Durable subagent registry/replay is the remaining producer class before Ops
replay can be considered complete.
