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
- [x] T005 [done-static] Define fallback behavior for unsupported clients.
  - 2026-04-29: `render_widget_fallback_markdown()` returns stable markdown or
    passive blocked text; Feature 005 chat still renders widget events as
    links/text, never iframes.
- [x] T006 [done-static] Document room-state vs chat-message distinction.
  - 2026-04-29: research now records widget-room-state/client-specific behavior
    and keeps chat fallback separate.

## Host Policy

- [x] T010 [done-static] Define widget proposal schema: title, url/resource, room, permissions,
  fallback text and audit refs.
  - 2026-04-29: `MatrixWidgetProposal` carries `proposal_id`, `room_id`,
    `title`, `url`, `resource_uri`, `permissions`, fallback text and audit refs.
- [x] T011 [done-static] Require user approval before agent writes widget state events.
  - 2026-04-29: `build_widget_state_event()` requires `MatrixWidgetApproval`
    with `status=approved`, matching proposal id and audit ref.
- [x] T012 [done-static] Add allowed origin/resource policy.
  - 2026-04-29: `MatrixWidgetHostPolicy.allowed_origins` and
    `allowed_resource_prefixes` fail closed; MCP resources can be evaluated via
    Feature 024.
- [x] T013 [done-static] Add sandbox/CSP policy for hosted app resources.
  - 2026-04-29: state-event drafts carry sandbox flags and generated CSP with
    allowlisted frame origins.
- [x] T014 [done-static] Add lifecycle: create, update, revoke, expire.
  - 2026-04-29: proposal/approval expiry is enforced and
    `build_widget_revoke_state_event()` creates deterministic revoke drafts.
- [x] T015 [done-static] Add per-room power-level checks.
  - 2026-04-29: state-event drafts require actor power level >= proposal or
    host default required level.
- [x] T016 [done-static] Add audit events for widget proposal and state mutation.
  - 2026-04-29: proposal and approval audit refs are embedded into state-event
    draft data; real audit persistence remains part of later bridge write path.
- [x] T017 [done-static] Link MCP resource metadata to Feature 024 policy.
  - 2026-04-29: `evaluate_widget_proposal(..., mcp_server=...)` calls
    Feature 024 `evaluate_resource_fetch_policy()` before hosting resources.

## UI

- T020 Keep safe link-card fallback in chat.
- T021 Add widget proposal approval UI.
- T022 Add widget status display in room details.
- T023 Add error/fallback display for clients without widget support.
- T024 Add report-artifact link integration from Feature 027.
- T025 Add A2UI handoff compatibility notes from Feature 008.

## Verification

- [x] T030 [done-static] Unit-test URL/resource allowlist.
- [x] T031 [done-static] Unit-test power-level/approval checks.
- [x] T032 [done-static] Unit-test fallback rendering.
- [x] T033 [done-static] Integration-test widget proposal to state event.
- T034 Playwright-test Matrix web chat fallback.
- T035 Live-test Element X/FluffyChat compatibility when devices are available.
- [x] T036 [done-static] Meta-Harness scenario: agent proposes widget, user approves, fallback
  remains safe.
  - 2026-04-29: `matrix-widget-policy` covers approved state-event draft,
    unsafe URL blocking and Feature 024 MCP resource denial.
