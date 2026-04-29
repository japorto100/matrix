---
title: Agent Ops Room Tool Observatory Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 029
---

# Research

## Local Z Reference

Derived from `Z_Hermes_Desktop_claw3d.md`.

## Working Judgement

Hermes/Claw3D is useful as a pattern, not as a direct dependency: make agent
work visible as operational state. Matrix should first build a dense 2D ops
board from existing traces; spatial/3D visualization is optional after the data
contract and usability are proven.

## Source Check 2026-04-29

- Hermes Desktop appears to use an Electron shell that starts/embeds a separate
  web workspace and adapter. The key lesson is process/adapter separation.
- Claw3D-style rooms are a visualization layer, not the agent runtime. Matrix
  should keep runtime, traces and UI separated the same way.
- For multi-agent systems, spatial metaphors can compress status, but they can
  also hide detail. Raw trace drilldown must remain available.

## Design Consequence

Build this path:

```text
trace/audit/Meta-Harness events -> ops event read model -> 2D control board
  -> optional spatial room adapter
```

No provider-specific runtime is implied.

## 2026-04-29 Static UI Follow-Up

`/control/ops` now implements the first dense 2D board using already available
Control data: sessions, normal tool catalog metadata and audit events. This is
deliberately not a new event store. It proves the frontend shape and leaves the
real read model, live stream and Meta-Harness replay endpoints as backend work.
