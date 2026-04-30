---
title: Agent Ops Room Tool Observatory Live Verify
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 029
---

# Live Verify

- LV001 Start dev stack and open Control UI ops room.
- LV001a Open `/control/ops?mode=dev` and verify static board renders without
  browser layout overflow.
- LV002 Run a simple agent session and verify live timeline events through
  `/api/v1/control/ops/events` and `/api/v1/control/ops/stream`.
- LV003 Trigger tool call and verify tool status/risk appears in the backend
  read model and frontend drilldown.
- LV004 Trigger approval-needed state and verify blocker/approval arrays plus
  frontend badges.
- LV005 Deny approval and verify audit/replay reflects denial.
- LV006 Run memory/RAG retrieval and verify markers appear.
- LV007 Replay a Meta-Harness run and verify candidate/gate/verdict timeline.
- LV008 [partial-static] Filter by agent/session/tool/risk/status and verify
  stable rendering.
- LV009 [done-static-live-smoke] Verify redacted sensitive fields in ops board.
- LV010 Verify Matrix handoff link opens correct room/context.
- LV011 Stress a long session and verify pagination/windowing.
- LV012 Prototype spatial/3D view only after 2D live gates pass.

## 2026-04-30 Added Live Gates

- LV030 Run a subagent scenario and verify parent/child rollup, role, depth,
  status, tool counts, token/request summary and output-tail.
- LV031 Run provider request and verify prompt-cache/request telemetry joins by
  session/turn/tool digest.
- LV032 Trigger pause/kill/status and verify action result events appear with
  redacted metadata.
