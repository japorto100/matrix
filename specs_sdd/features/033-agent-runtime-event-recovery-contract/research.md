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

2026-04-30 Meta-Harness gate update: runtime events are no longer only a UI
surface. `TraceExpectations` can assert nested runtime event names and metadata
shape inside audit rows, including wildcard forbidden metadata keys. The
provider-free routing contract now includes `llm.prompt_cache_break` as a
redaction-shape scenario, so cache diagnostics must expose request id, provider
model and cache counters without raw prompts, raw headers, authorization values,
resolved secrets or unredacted request telemetry. This references the same
runtime-event contract described in the fresh Z_ agent harness notes while
remaining provider-agnostic.

2026-04-30 subagent harness update: value-level runtime metadata assertions now
cover the child isolation contract. The provider-free contract requires
`subagent.delegation.accepted/started/completed`, a
`subagent.parent_memory_handoff` digest and a `memory.retain.blocked` event.
It asserts `context_mode=isolated`, `memory_write_policy=parent_only`, child
allowlist membership for `semantic_lookup` and absence of `memory_add`. This
ports the Hermes child-tool isolation lesson into Matrix's event contract
without treating Hermes' CLI execution model as a product runtime template.

2026-04-30 replay identity update: the backend event envelope now carries the
fields downstream replay actually needs: run/session/thread/turn identity,
span/parent identity, payload and an explicit redaction policy marker. This
continues the same Z_ agent-harness and Hermes/OpenClaw lesson: UI and Ops
should reconstruct tool, memory, retrieval and subagent state from stable
events, not from assistant prose or provider-specific traces. The change is
additive and provider-agnostic; older callers get derived IDs while scoped RAG
calls now preserve thread/session identity in their own runtime events.

2026-04-30 taxonomy update: Feature 033 now treats kind and outcome as backend
contract, not UI convention. `RUNTIME_EVENT_KIND_DEFINITIONS` gives each
producer family stable name prefixes for agent lifecycle, model, tool, memory,
retrieval, KG, artifact, subagent, MCP, Matrix and control events.
`metadata.outcome` is normalized to `ok`, `error`, `timeout`, `killed`,
`cancelled`, `stale` or `deferred` while preserving explicit producer outcomes
such as confirmed session kill. The provider-free routing contract checks this
directly through `routing-runtime-event-kind-outcome-taxonomy`, keeping replay
semantics independent of LiteLLM/OpenRouter/provider telemetry and independent
of the Control/Ops frontend.

2026-04-30 subagent replay rollup update: the Control/Ops backend now joins
`subagent` lifecycle events with the parent-side
`subagent.parent_memory_handoff` memory event by `child_task_id`. This is
important because the handoff deliberately belongs to the parent memory lane,
not to the child lifecycle lane. The replay row now carries normalized outcome,
terminal reason, result digest and parent-curation metadata while still showing
kill/pause/replay as unsupported until a durable child registry exists.

2026-04-30 tool-result runtime propagation update: tools can now emit nested
runtime events in their result payload, and `tool_node` appends those events to
the run state after the canonical `tool.*` event. This is needed for
`retrieve_context`: the RAG/KG retrieval events and
`artifact.rag_kg_sources.ready` event are downstream UI/Ops facts, not model
text. The full tool result still goes to UI/audit, but the next LLM turn gets
the tool's compact `to_model_output()` instead.

2026-04-30 LLM failure replay update: failed provider calls now produce a
redacted `llm.call.failed` runtime event before the original exception
continues to the runner. This closes an observability gap between span-only
LLM errors and audit-backed replay. The event stores provider, model,
error type and classifier output (`reason`, `recovery`, `retryable`,
`status_code`) but never the raw user prompt or provider request body.
