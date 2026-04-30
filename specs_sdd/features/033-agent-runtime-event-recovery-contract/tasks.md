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

- T010 Emit runtime events from current agent loop without changing behavior.
- T011 Add subagent registry model for accepted, started, completed, failed,
  timed out, killed and stale runs.
- T012 Add gated single-hop subagent execution with default-off/fail-closed
  policy.
- T013 Add parent-side memory handoff event for delegation outcomes.
- T014 Add status/kill/pause/replay control intents where backend support
  exists; unsupported controls must return structured unsupported events.

## UI And Harness

- T020 Surface runtime events in Agent Chat downstream cards.
- T021 Surface runtime events in Control/Ops tabs.
- T022 Add Meta-Harness gates for event completeness and redaction.

