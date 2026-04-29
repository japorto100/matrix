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
- T002 Define `AgentOpsEvent` schema.
- T003 Define session timeline aggregation.
- T004 Define agent status derivation rules.
- T005 Define blocker/approval state mapping.
- T006 Define tool-risk annotations from Feature 024.
- T007 Define replay contract for historical runs.

## UI

- T010 Add dense 2D ops board in Control UI.
- T011 Add timeline view for one session/run.
- T012 Add tool-call drilldown with approval and audit refs.
- T013 Add memory/RAG/KG event markers.
- T014 Add filters by agent, session, tool, risk and status.
- T015 Add Matrix room handoff/action links.
- T016 Evaluate optional spatial/3D room after 2D usability passes.

## Backend

- T020 Add ops event read model from traces/audit.
- T021 Add live stream endpoint for ops events.
- T022 Add replay endpoint for Meta-Harness run id.
- T023 Add retention and redaction policy.
- T024 Add server-side pagination/windowing for long sessions.
- T025 Add health and lag metrics.

## Verification

- T030 Unit-test status derivation.
- T031 Unit-test redaction.
- T032 Integration-test trace-to-ops-event read model.
- T033 Playwright-test ops board.
- T034 Live-verify active agent session appears in ops room.
- T035 Live-verify blocked approval state.
- T036 Live-verify Meta-Harness replay.
- T037 Usability-gate optional 3D/spatial prototype before promotion.
