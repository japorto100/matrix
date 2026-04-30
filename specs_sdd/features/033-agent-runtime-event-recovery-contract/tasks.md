---
title: Agent Runtime Event Recovery Tasks
status: planned
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 033
---

# Tasks

## Contract

- [x] T001 [done-static] Define event envelope: event id, run id, session id, turn id, parent id,
  span id, timestamp, kind, status, payload and redaction marker.
  - 2026-04-30: `agent.runtime_events.make_runtime_event()` now emits the
    complete provider-agnostic envelope. Missing `run_id`, `session_id`,
    `turn_id`, `span_id` and `parent_id` are derived without breaking older
    callers, and metadata/payload are redacted before replay.
- [x] T002 [done-static] Define event kinds for agent lifecycle, model request, tool call/result,
  memory, retrieval, KG claim, artifact and subagent lifecycle.
- [x] T003 [done-static] Define outcome taxonomy: ok, error, timeout, killed, cancelled, stale
  and deferred.
  - 2026-04-30: `agent.runtime_events` now exposes provider-agnostic kind
    definitions with allowed event-name prefixes for run/turn/LLM/tool/memory/
    RAG/KG/artifact/subagent/MCP/Matrix/control events. `make_runtime_event()`
    also adds a stable `metadata.outcome` taxonomy without overriding explicit
    caller outcomes, and maps timeout/kill cases separately from generic stale
    or cancelled status.
- [x] T004 [done-static] Define payload caps and output-tail policy.
  - 2026-04-30: runtime events cap strings/lists through the shared redaction
    path and record `runtime-event-redaction/v1` policy metadata on every
    event.

## Runtime

- [x] T010 Emit runtime events from current agent loop without changing behavior.
  - 2026-04-30: LLM runtime events are emitted from both SimpleLoop and
    LangGraph outputs; A2A subagent events now use the same envelope.
  - 2026-04-30: memory recall/retain nodes emit the same envelope for
    unavailable, blocked, completed, failed and timeout/stale outcomes.
  - 2026-04-30: successful memory recall/retain and retain-timeout audit rows
    persist the same runtime envelopes for replay.
  - 2026-04-30: tool execution emits `tool` runtime events for started,
    completed, failed and timeout/stale paths, preserving `tool_call_id` and
    result-key metadata without inlining tool output.
  - 2026-04-30: retrieval API emits RAG runtime events for start/completion and
    KG selection events when claims survive context-bubble selection.
  - 2026-04-30: scoped retrieval calls persist the same redacted RAG/KG runtime
    events into audit metadata for Ops replay, without storing raw query text.
  - 2026-04-30: control-plane MCP/skill reload and skill toggle/import emit
    `control` runtime events (`cache.invalidated`/`cache.unchanged`) carrying
    only cache-impact digests and action metadata.
  - 2026-04-30: LLM prompt-cache changes now emit
    `llm.prompt_cache_break` runtime events with cache-break reasons, digests,
    request id and cache-read counters, instead of requiring downstream
    surfaces to parse request telemetry internals.
  - 2026-04-30: tool execution now propagates tool-result nested
    `runtime_events` into the run state after the normal `tool.*` event. This
    lets `retrieve_context` forward `rag.retrieve.*`, `kg.*` and
    `artifact.rag_kg_sources.ready` events to Agent Chat/Control without
    treating full tool output as event payload.
- [partial-static] T011 Add subagent registry model for accepted, started, completed, failed,
  timed out, killed and stale runs.
  - 2026-04-30: runtime event stream covers accepted/started/completed/failed
    and timeout-as-stale for A2A child attempts. Durable registry and kill
    state remain Control follow-ups.
  - 2026-04-30: Ops now derives a replayable `subagent_runs` read-model from
    audited runtime events, grouped by child task id. This is the static
    registry/read-model bridge; durable process registry and kill/pause remain
    future work.
  - 2026-04-30: the Ops bridge now correlates `subagent` lifecycle events with
    the `subagent.parent_memory_handoff` memory event. Run rows expose outcome,
    terminal reason, result digest, lifecycle count and parent-curation status
    without changing the child memory-write policy.
- [x] T012 Add gated single-hop subagent execution with default-off/fail-closed
  policy.
  - 2026-04-30: A2A execution is blocked unless
    `AGENT_A2A_MAX_SPAWN_DEPTH` permits the next hop; blocked attempts emit a
    structured subagent runtime event.
  - 2026-04-30: accepted child requests now turn Matrix delegation context into
    runtime state: role, parent thread, spawn depth, isolated context mode,
    allowed tools and parent-only memory policy. Ordinary chat context does not
    become policy unless the request is an `a2a-*` child request with the
    Matrix delegation prefix.
  - 2026-04-30: inbound child context is policy-filtered again at the server
    boundary. A forged `allowed_tools` list cannot enable forbidden child tools
    because the app reuses the provider-agnostic child tool policy before
    constructing `AgentExecutionContext`.
  - 2026-04-30: Meta-Harness routing contract now verifies the same policy at
    trace level: isolated context, parent-only memory, narrow child allowlist
    and no direct `memory_add`.
- [x] T013 Add parent-side memory handoff event for delegation outcomes.
  - 2026-04-30: completed child results emit a parent-only memory handoff
    event with digest and no raw output payload.
  - 2026-04-30: child-side durable retain attempts are blocked by the Memory
    node with a redacted runtime event, so the parent handoff remains the only
    durable-memory path for delegated outcomes.
  - 2026-04-30: provider-free contract scenario requires
    `subagent.parent_memory_handoff` plus `memory.retain.blocked`, making
    parent-side curation a trace gate rather than an implementation comment.
- [partial-static] T014 Add status/kill/pause/replay control intents where backend support
  exists; unsupported controls must return structured unsupported events.
  - 2026-04-30: `/api/v1/control/sessions/{thread_id}/status` returns a
    supported status runtime event, `/kill` requires explicit confirmation
    before checkpoint/session cancellation, and `/pause` plus `/replay` return
    explicit unsupported `control` runtime events.

## UI And Harness

- [x] T020 Surface runtime events in Agent Chat downstream cards.
  - 2026-04-30: `AgentChatEventRail` renders runtime-event counts/statuses
    from stream metadata and keeps request telemetry/cache diagnostics separate.
- [x] T021 Surface runtime events in Control/Ops tabs.
  - 2026-04-30: `agent.control.ops` exposes redacted runtime events from audit
    metadata in `agent-ops-event/v1`, and `/control/ops` renders Runtime Lanes
    with kind/status rollups and event drilldown.
  - 2026-04-30: LLM, Tool, Memory and scoped RAG/KG producers now write runtime
    events into audit metadata, giving Ops real replay input beyond frontend
    stream state.
  - 2026-04-30: Subagent lifecycle events are also persisted through audit and
    surfaced as `/control/ops` subagent run rows with explicit unsupported
    control states.
- [x] T022 Add Meta-Harness gates for event completeness and redaction.
  - 2026-04-30: `TraceExpectations` can now require nested runtime event
    names, required/forbidden runtime-event metadata keys and required/
    forbidden metadata values. The routing contract suite includes provider-free
    `llm.prompt_cache_break` and subagent-isolation gates that fail on raw
    prompts, headers, authorization material, resolved secrets, unredacted
    request telemetry or child memory/tool policy drift.
  - 2026-04-30: `routing-runtime-event-replay-identity` now proves replayable
    event identity provider-free: `run_id`, `session_id`, `thread_id`,
    `turn_id`, `span_id`, payload and redaction policy must be present, and
    payload secrets must be redacted.
  - 2026-04-30: `routing-runtime-event-kind-outcome-taxonomy` now gates the
    runtime taxonomy itself: LLM/tool/memory/subagent/control events must carry
    matching kind/name prefixes and stable outcomes (`deferred`, `ok`,
    `timeout`, `killed`) for replay.
