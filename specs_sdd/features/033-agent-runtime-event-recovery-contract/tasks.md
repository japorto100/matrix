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
- [partial-static] T011 Add subagent registry model for accepted, started, completed, failed,
  timed out, killed and stale runs.
  - 2026-04-30: runtime event stream covers accepted/started/completed/failed
    and timeout-as-stale for A2A child attempts. Durable registry and kill
    state remain Control follow-ups.
- [x] T012 Add gated single-hop subagent execution with default-off/fail-closed
  policy.
  - 2026-04-30: A2A execution is blocked unless
    `AGENT_A2A_MAX_SPAWN_DEPTH` permits the next hop; blocked attempts emit a
    structured subagent runtime event.
- [x] T013 Add parent-side memory handoff event for delegation outcomes.
  - 2026-04-30: completed child results emit a parent-only memory handoff
    event with digest and no raw output payload.
- T014 Add status/kill/pause/replay control intents where backend support
  exists; unsupported controls must return structured unsupported events.

## UI And Harness

- T020 Surface runtime events in Agent Chat downstream cards.
- T021 Surface runtime events in Control/Ops tabs.
- T022 Add Meta-Harness gates for event completeness and redaction.
