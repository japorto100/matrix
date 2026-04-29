---
title: Matrix Widget App Host Tasks
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 030
---

# Tasks

## Compatibility

- T001 Verify current Tuwunel version widget event behavior.
- T002 Verify Element Web/Matrix Web widget rendering for `m.widget` and
  `im.vector.modular.widgets`.
- T003 Verify Element X support and limitations.
- T004 Verify FluffyChat support and limitations.
- T005 Define fallback behavior for unsupported clients.
- T006 Document room-state vs chat-message distinction.

## Host Policy

- T010 Define widget proposal schema: title, url/resource, room, permissions,
  fallback text and audit refs.
- T011 Require user approval before agent writes widget state events.
- T012 Add allowed origin/resource policy.
- T013 Add sandbox/CSP policy for hosted app resources.
- T014 Add lifecycle: create, update, revoke, expire.
- T015 Add per-room power-level checks.
- T016 Add audit events for widget proposal and state mutation.
- T017 Link MCP resource metadata to Feature 024 policy.

## UI

- T020 Keep safe link-card fallback in chat.
- T021 Add widget proposal approval UI.
- T022 Add widget status display in room details.
- T023 Add error/fallback display for clients without widget support.
- T024 Add report-artifact link integration from Feature 027.
- T025 Add A2UI handoff compatibility notes from Feature 008.

## Verification

- T030 Unit-test URL/resource allowlist.
- T031 Unit-test power-level/approval checks.
- T032 Unit-test fallback rendering.
- T033 Integration-test widget proposal to state event.
- T034 Playwright-test Matrix web chat fallback.
- T035 Live-test Element X/FluffyChat compatibility when devices are available.
- T036 Meta-Harness scenario: agent proposes widget, user approves, fallback
  remains safe.
