---
title: Appservice NATS E2EE Bridges Research
status: draft
owner: filip
created: 2026-04-30
updated: 2026-04-30
feature_id: 006
---

# Research

## Hermes Matrix Adapter Follow-Up 2026-04-30

Derived from the fresh `_ref/hermes-agent` pull and related Matrix adapter
changelog notes. This is directly relevant to Matrix transport behavior, not a
CLI-agent architecture import.

Reusable bug classes for Matrix:

- echo/pairing loops can happen when bridge/session markers are not strict
  enough.
- group-room free-response, mention routing and thread-root preservation need
  explicit gates so the agent does not answer every room event.
- approval reactions must bind to the intended event/thread and cannot be
  accepted as generic room reactions.
- reconnect/session replay must not revive stale approvals or duplicate agent
  responses.
- E2EE/cross-signing bootstrap blockers should surface as operational blockers
  instead of silent degraded behavior.

Matrix-local consequence:

- Feature 006 keeps Go appservice crypto ownership and Python cleartext NATS
  handoff.
- The Hermes signal becomes live/static gates around event filtering, session
  markers, approval binding and reconnect behavior.
- No Hermes CLI gateway structure or provider-specific prompt format is copied.

## Static Implementation Note 2026-04-30

Implemented in `python-backend/bridge`:

- agent-sender echo guard for reflected appservice events.
- in-memory `event_id` replay dedupe to block reconnect duplicate replies.
- malformed thread reply fail-closed when `is_thread_reply=true` arrives
  without `thread_id`.
- Matrix event id, target agent and thread-reply marker propagated into Agent
  Chat context for trace/debug visibility.

Still open:

- live reconnect with NATS/appservice.
- reaction-bound approval events.
- E2EE/xsign bootstrap blocker surfacing.

Related fresh local inputs:

- `Z_matrix_widgets_formulars_and so on.md` for Matrix room-state/widget
  compatibility pressure.
- Feature 030 research for the rule that Matrix room output must remain
  mobile-compatible with markdown/link/event fallbacks.
