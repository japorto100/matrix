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

2026-04-30 implementation update: LLM, tool execution, memory recall/retain,
scoped RAG/KG retrieval and A2A subagent lifecycle now persist runtime-event
envelopes into audit metadata. Ops derives a static `subagent_runs` read-model
from those events. Durable child process registry, kill/pause/replay controls
and cost/token rollups remain the next reliability layer, not a blocker for
audit replay.

2026-04-30 cache-control update: MCP reload and skill reload/toggle/import now
produce the same runtime event envelope with kind `control`. The payload carries
only cache-impact digests, source/reason and rebind/no-change action metadata,
so Ops and prompt-cache replay can show invalidation without leaking prompt,
tool schema or skill body text.

2026-04-30 session-control update: the legacy destructive session delete is now
paired with explicit control endpoints. Kill requires confirmation on the new
endpoint and records checkpoint deletion/session cancellation as a runtime
event; pause and replay intentionally return unsupported runtime events instead
of pretending capability exists. This matches the Hermes lesson: operator
controls must be observable even before every control is durable.

2026-04-30 child-policy update: A2A child context is now runtime state, not
only prompt text. The app accepts policy only for Matrix-owned `a2a-*` child
requests with the delegation prefix, filters provider tool definitions to the
child allowlist and propagates parent-only memory policy into both runners.
Memory retain then emits a blocked runtime event before durable Memory access.
This strengthens the subagent event contract because `parent_memory_handoff`
is now the only write-intended path for delegated outcomes.
