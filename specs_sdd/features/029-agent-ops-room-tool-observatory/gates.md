---
title: Agent Ops Room Tool Observatory Gates
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 029
---

# Gates

- [x] G001 Ops room derives from trace/audit data, not separate hidden state in
  static frontend coverage.
- [x] G002 Approval/blocker state is visible in one screen in static frontend
  coverage.
- [x] G003 Redaction applies before rendering tool inputs/outputs in backend
  ops events and frontend drilldown.
- [x] G004 Tool risk from Feature 024 is visible next to tool events in static
  frontend coverage when catalog metadata is present.
- [x] G005 Replay mode and live mode use the same event contract for static
  ops snapshot and SSE `ops_snapshot` events.
- [x] G006 Long sessions remain performant with pagination/windowing through
  backend `limit`/`offset` bounds.
- [x] G007 Optional 3D/spatial view cannot replace the dense 2D control surface.
- G008 Matrix handoff links respect user/room permissions.
- G009 Meta-Harness replay shows candidate, gates and verdicts.
