---
title: Agent Ops Room Tool Observatory Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 029
---

# Tasks

## Event Model

- T001 Inventory traces, sessions, tool calls, approvals and Meta-Harness run
  artifacts.
- [x] T002 [done-static] Define `AgentOpsEvent` schema.
  - 2026-04-29: `/api/v1/control/ops/events` returns
    `agent-ops-event/v1` with source, type, status, thread, role, tool, risk,
    approval/audit refs and redacted payloads.
- [x] T003 [done-static] Define session timeline aggregation.
  - 2026-04-29: backend read model aggregates redacted ops events into session
    rows with status, checkpoint count, event count and tool count.
- [x] T004 [done-static] Define agent status derivation rules.
  - 2026-04-29: failed audit events become `blocked`, approval/consent actions
    become `needs_approval`, tool events become `active`, otherwise `waiting`
    or `replay`.
- [x] T005 [done-static] Define blocker/approval state mapping.
  - 2026-04-29: ops read model emits dedicated `blockers` and `approvals`
    arrays from the same event contract.
- [x] T006 [done-static] Define tool-risk annotations from Feature 024.
  - 2026-04-29: backend joins ToolRegistry catalog risk metadata into ops
    events; frontend displays risk in board and drilldown.
- T007 Define replay contract for historical runs.

## UI

- [x] T010 [done-static] Add dense 2D ops board in Control UI.
  - 2026-04-29: `/control/ops` renders a Developer Mode board from existing
    sessions, tool catalog and audit query surfaces with active/waiting/blocked
    status, tool-risk badges, blocker cards, audit drilldown link and Matrix
    handoff link.
- [x] T011 [done-static] Add timeline view for one session/run.
  - 2026-04-29: `/control/ops` consumes the ops event read model and shows a
    tool timeline from the normalized contract.
- [x] T012 [done-static] Add tool-call drilldown with approval and audit refs.
  - 2026-04-29: selected timeline events show tool, risk, status, audit ref,
    approval ref, duration, error and redacted input/output/metadata JSON.
- [x] T013 [done-static] Add memory/RAG/KG event markers.
  - 2026-04-29: backend classifies audit actions/tool names into `memory`,
    `rag`, `kg`, `approval`, `tool_call` or `trace`.
- [x] T014 [done-static] Add filters by agent, session, tool, risk and status.
  - 2026-04-29: backend supports agent/session/tool/risk/status filters;
    frontend exposes status, risk and tool filters.
- T015 Add Matrix room handoff/action links.
- T016 Evaluate optional spatial/3D room after 2D usability passes.

## Backend

- [x] T020 [done-static] Add ops event read model from traces/audit.
  - 2026-04-29: `agent.control.ops.build_ops_read_model()` derives redacted
    ops events from audit rows and session checkpoints without a new store.
- [x] T021 [done-static] Add live stream endpoint for ops events.
  - 2026-04-29: `/api/v1/control/ops/stream` emits SSE `ops_snapshot` events
    using the same `agent-ops-event/v1` contract as `/ops/events`.
- T022 Add replay endpoint for Meta-Harness run id.
- T023 Add retention and redaction policy.
- T024 Add server-side pagination/windowing for long sessions.
- T025 Add health and lag metrics.

## Verification

- [x] T030a [done-static] Frontend typecheck/lint for `/control/ops`.
- [x] T030 [done-static] Unit-test status derivation.
- [x] T031 [done-static] Unit-test redaction.
- [x] T032 [done-static] Integration-test trace-to-ops-event read model.
- T033 Playwright-test ops board.
- T034 Live-verify active agent session appears in ops room.
- T035 Live-verify blocked approval state.
- T036 Live-verify Meta-Harness replay.
- T037 Usability-gate optional 3D/spatial prototype before promotion.
