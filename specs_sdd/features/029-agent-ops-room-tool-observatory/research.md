---
title: Agent Ops Room Tool Observatory Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-30
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

## 2026-04-29 Read Model Follow-Up

The ops room now has a backend event contract instead of only frontend-derived
state. `agent-ops-event/v1` is built from existing audit/session data and
classifies events into trace, tool call, approval, memory, RAG and KG markers.
Sensitive fields are recursively redacted before JSON reaches the frontend.

The same contract powers `/api/v1/control/ops/events` and the SSE
`/api/v1/control/ops/stream` endpoint, so live mode and replay mode do not fork
UI semantics. The frontend now consumes that read model, exposes status/risk/tool
filters and shows a tool-call drilldown with audit and approval references.

Meta-Harness replay remains open because it needs a run-id adapter over Feature
016 artifacts, but it should emit the same `AgentOpsEvent` shape.

## 2026-04-30 Matrix Transport Marker Follow-Up

The fresh `_ref/hermes-agent` Matrix adapter updates add concrete event classes
the ops room should make visible once Feature 006 emits them:

- ignored self/echo events and pairing-loop suppressions.
- group-room mention/thread/free-response routing decisions.
- approval reaction binding and stale approval rejection.
- reconnect/session replay markers.
- E2EE/cross-signing bootstrap blockers.

This is not a Hermes UI import. It is an observability consequence: the Matrix
runtime should surface these transport/session decisions through the same
`AgentOpsEvent` read model used for tool, approval, memory, RAG and KG events.

2026-04-30 implementation follow-up: the backend read model now recognizes
Matrix transport/session audit rows directly. Known blocker classes such as
`echo_loop_blocked`, `mention_required`, `approval_reaction_wait`,
`reconnect_replay`, `e2ee_bootstrap_required` and `xsign_bootstrap_required`
become first-class `matrix_transport` ops events with room/event/thread ids
when present. This keeps the frontend dense 2D board useful for Matrix-native
agent failures without importing Hermes' UI model.
