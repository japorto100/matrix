---
title: Matrix Widget App Host Research
status: draft
owner: filip
created: 2026-04-29
updated: 2026-04-29
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
- SOTA web check 2026-04-29:
  - `matrix-widget-api` latest visible npm release is 1.13.1 and its readme
    still warns widgets are not yet in the Matrix spec, so Matrix widget
    behavior must be treated as client/toolkit-specific rather than universal.
  - Matrix.org TWIM 2026-01-09 confirms active Matrix Widget Toolkit work,
    including custom CSP `frame-src` support in
    `@matrix-widget-toolkit/widget-server` 1.2.0. This directly supports the
    local host policy choice to model sandbox/CSP and frame origins explicitly.
  - `matrix-js-sdk` raw changelog shows recent widget-adjacent changes in the
    40.x line, including `RoomWidgetClient` sticky event support. The
    implementation should keep room-state/sticky-event semantics separate from
    plain chat-message rendering.
- Local implementation 2026-04-29:
  - `agent.matrix_widgets.policy` defines provider-free proposal, approval,
    allowlist, power-level, lifecycle revoke and fallback contracts.
  - `meta_harness matrix-widget-policy` writes deterministic artifacts for
    approved state-event draft, unsafe URL blocking and Feature 024 MCP resource
    handoff denial.

## Design Consequence

The safe pipeline is:

```text
agent proposes widget/app -> policy + room permission + user approval
  -> room-state widget or hosted app link -> fallback markdown/link
```

Feature 005's current link-card behavior stays the baseline until this feature
proves a sandboxed app host.
