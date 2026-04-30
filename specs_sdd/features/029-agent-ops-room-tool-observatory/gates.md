---
title: Agent Ops Room Tool Observatory Gates
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-30
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
- [x] G010 Matrix transport/session blockers from Feature 006 are visible as
  first-class ops events, not buried in raw logs.
  - 2026-04-30: static backend coverage proves Matrix transport audit rows
    become `matrix_transport` ops events with `blocker_reason` and room/event
    ids, and approval reaction waits are counted in the approval lane.

## 2026-04-30 Added Gates

- [ ] Subagent states distinguish active, stale, recently ended, timeout,
  killed and completed.
- [ ] Tool/model/memory/RAG/KG event lanes render capped output tails.
- [ ] Status/kill/pause/replay controls return explicit supported or
  unsupported outcomes.
- [ ] Ops events link to Prompt Cache and Report Artifact surfaces.
