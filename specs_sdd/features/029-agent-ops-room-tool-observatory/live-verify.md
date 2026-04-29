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
- LV002 Run a simple agent session and verify live timeline events.
- LV003 Trigger tool call and verify tool status/risk appears.
- LV004 Trigger approval-needed state and verify blocker display.
- LV005 Deny approval and verify audit/replay reflects denial.
- LV006 Run memory/RAG retrieval and verify markers appear.
- LV007 Replay a Meta-Harness run and verify candidate/gate/verdict timeline.
- LV008 Filter by agent/session/tool and verify stable rendering.
- LV009 Verify redacted sensitive fields in ops board.
- LV010 Verify Matrix handoff link opens correct room/context.
- LV011 Stress a long session and verify pagination/windowing.
- LV012 Prototype spatial/3D view only after 2D live gates pass.
