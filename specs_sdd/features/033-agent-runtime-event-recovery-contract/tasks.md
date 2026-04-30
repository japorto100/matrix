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

- T001 Define event envelope: event id, run id, session id, turn id, parent id,
  span id, timestamp, kind, status, payload and redaction marker.
- T002 Define event kinds for agent lifecycle, model request, tool call/result,
  memory, retrieval, KG claim, artifact and subagent lifecycle.
- T003 Define outcome taxonomy: ok, error, timeout, killed, cancelled, stale
  and deferred.
- T004 Define payload caps and output-tail policy.

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
- [partial-static] T011 Add subagent registry model for accepted, started, completed, failed,
  timed out, killed and stale runs.
  - 2026-04-30: runtime event stream covers accepted/started/completed/failed
    and timeout-as-stale for A2A child attempts. Durable registry and kill
    state remain Control follow-ups.
  - 2026-04-30: Ops now derives a replayable `subagent_runs` read-model from
    audited runtime events, grouped by child task id. This is the static
    registry/read-model bridge; durable process registry and kill/pause remain
    future work.
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
- [x] T013 Add parent-side memory handoff event for delegation outcomes.
  - 2026-04-30: completed child results emit a parent-only memory handoff
    event with digest and no raw output payload.
  - 2026-04-30: child-side durable retain attempts are blocked by the Memory
    node with a redacted runtime event, so the parent handoff remains the only
    durable-memory path for delegated outcomes.
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
    names and required/forbidden runtime-event metadata keys. The routing
    contract suite includes a provider-free `llm.prompt_cache_break` redaction
    shape gate that fails on raw prompts, headers, authorization material,
    resolved secrets or unredacted request telemetry.
