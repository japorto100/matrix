---
title: Matrix Widget App Host Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-30
feature_id: 030
---

# Research

## Local Z Reference

Derived from `Z_matrix_widgets_formulars_and so on.md`.

## Working Judgement

The note is directionally useful but must be verified against actual Matrix
client behavior. Matrix agents should not "send arbitrary apps in chat".
Instead, they can propose room-state widgets or safe links/artifacts, and the
host/client decides what can render.

## Source Check 2026-04-29

- Matrix widgets are primarily room-state/configured app surfaces, not a
  universal message-body app protocol.
- Element-family and third-party clients differ in widget support. Markdown and
  code blocks are safe common denominator; interactive widgets need fallback.
- MCP Apps-style resources and Matrix widgets are conceptually adjacent, but
  Matrix must gate them through local policy and client compatibility.
- SOTA/package check 2026-04-29:
  - npm registry reports `matrix-js-sdk` latest as 41.4.0 and
    `matrix-widget-api` latest as 1.17.0. The frontend now pins ranges to
    `matrix-js-sdk` `^41.4.0` and direct `matrix-widget-api` `^1.17.0` so
    widget parsing is not an undeclared transitive dependency.
  - `matrix-widget-api` 1.17.0 exposes `WidgetParser.parseRoomWidget()` and
    validates widget room-state events against `id`, `creatorUserId`, `type`
    and URL. The local webclient should use that parser for Matrix-shaped
    widget events, then layer Matrix-local approval/sandbox policy on top.
  - Matrix widget behavior must still be treated as client/toolkit-specific
    rather than universal because Element-family and third-party clients differ
    in support.
  - Matrix.org TWIM 2026-01-09 confirms active Matrix Widget Toolkit work,
    including custom CSP `frame-src` support in
    `@matrix-widget-toolkit/widget-server` 1.2.0. This directly supports the
    local host policy choice to model sandbox/CSP and frame origins explicitly.
  - `matrix-js-sdk` changelog shows 41.4.0 released on 2026-04-28. Widget-
    adjacent changes remain relevant from the 40.x line, including
    `RoomWidgetClient` sticky event support. The implementation should keep
    room-state/sticky-event semantics separate from plain chat-message
    rendering.
- Local implementation 2026-04-29:
  - `agent.matrix_widgets.policy` defines provider-free proposal, approval,
    allowlist, power-level, lifecycle revoke and fallback contracts.
  - `meta_harness matrix-widget-policy` writes deterministic artifacts for
    approved state-event draft, unsafe URL blocking and Feature 024 MCP resource
    handoff denial.
  - The own Matrix webclient now parses `m.widget` and
    `im.vector.modular.widgets` via `matrix-widget-api` and renders approved
    policy widgets as sandboxed iframes while keeping unapproved/unsafe widgets
    as fallback cards.
  - Feature 027 report artifacts now have a Matrix widget handoff path:
    backend state-event drafts carry report manifest id/path, output path and
    renderer metadata; the webclient displays those fields as passive card
    metadata, not as executable report content.
  - Control UI now has a provider-agnostic widget approval read model:
    `/api/control/widgets/proposals` derives policy-evaluated proposal items
    from report artifacts and `/control/widgets` renders pending/approved/
    blocked state, denial reasons, audit refs and report metadata. It does not
    write Matrix room state; approve/deny mutation remains a live-gated bridge
    step.

## A2UI Handoff Compatibility Notes 2026-04-30

Feature 008 remains the rich agent UI boundary. Matrix widgets should not
become a hidden second A2UI runtime:

- A2UI packets and local/custom widgets render in Agent Chat UI surfaces.
- MCP Apps, tool dashboards, approval forms and code widgets stay in Agent
  Chat UI / Feature 008 unless explicitly converted into mobile-safe Matrix
  event summaries.
- Matrix room output must always be representable as text/link/media/file/event
  fallback first. Optional `m.widget` metadata may point to the same artifact
  but must pass Feature 030 approval and Feature 024 resource policy.
- Provider-specific UI SDK patterns may inform renderer ergonomics, but the
  Matrix contract remains provider-agnostic and client-compatibility driven.

## Design Consequence

The safe pipeline is:

```text
agent proposes widget/app -> policy + room permission + user approval
  -> Matrix event summary + optional room-state widget metadata
  -> fallback markdown/link/card in Matrix clients
```

ADR-0010 scopes Matrix rooms to mobile-compatible primitives. Feature 005's
message/link/card behavior stays the baseline. Rich MCP Apps, code widgets,
tool dashboards and A2UI surfaces move through Agent Chat UI rather than Matrix
timeline iframe hosting.

## Hermes Matrix Adapter Follow-Up 2026-04-30

The fresh `_ref/hermes-agent` Matrix adapter changes are directly relevant as
bug-class signals for widget handoff, even though Hermes is CLI-first:

- widget/report approvals must bind to the originating room event/thread, not
  any later reaction.
- reconnect/session replay must not re-open stale widget approvals.
- group-room free-response rules matter because widget proposals should not be
  emitted from every observed room event.
- echo/pairing-loop suppression is required before any optional room-state
  widget write is live-gated.

Feature 030 therefore depends on Feature 006 transport/session hygiene before
live Matrix widget approval writes. Until then, the webclient/control surfaces
may parse and display proposals, but Matrix room-state mutation remains gated.
