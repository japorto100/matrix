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

## Design Consequence

The safe pipeline is:

```text
agent proposes widget/app -> policy + room permission + user approval
  -> room-state widget or hosted app link -> fallback markdown/link
```

Feature 005's current link-card behavior stays the baseline until this feature
proves a sandboxed app host.
