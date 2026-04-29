---
title: Matrix Widget App Host Live Verify
status: planned
owner: filip
created: 2026-04-29
updated: 2026-04-29
feature_id: 030
---

# Live Verify

- LV001 Send safe widget state event in dev room and verify fallback link-card.
- LV002 Send unsafe widget URL and verify passive blocked text.
- LV003 Agent proposes a widget and approval UI appears.
- LV004 Deny proposal and verify no state event is written.
- LV005 Approve proposal and verify state event is written once.
- LV006 Verify room power-level failure is surfaced cleanly.
- LV007 Verify hosted app/resource origin allowlist.
- LV008 Verify widget revoke/expire lifecycle.
- LV009 Verify report artifact link from Feature 027 renders safely.
- LV010 Verify MCP resource handoff passes Feature 024 policy.
- LV011 Test Element Web/Matrix Web rendering.
- LV012 Test Element X behavior if local/mobile device is available.
- LV013 Test FluffyChat behavior if local/mobile device is available.
- [x] LV014 [done-static-live-smoke] Run Meta-Harness widget proposal scenario.
  - 2026-04-29: provider-free `matrix-widget-policy` live smoke passed 3/3
    scenarios and wrote `matrix_widget_policy.json`.
  - 2026-04-29 live-smoke:
    `run-matrix-widget-policy-20260429-rerun` passed in
    `/tmp/matrix-meta-harness-widget-policy-rerun`.
- LV015 Open own Matrix webclient and verify an approved policy widget renders
  as a sandboxed iframe only when audit/approval metadata is present.
- LV016 Open own Matrix webclient and verify the same safe widget URL without
  approval metadata remains fallback-only and never embeds an iframe.
- LV017 Open room info in own Matrix webclient and verify active room-state
  widgets list status, origin and blocked reason.
- LV018 Verify `matrix-js-sdk` 41.4.0 + `matrix-widget-api` 1.17.0 room widget
  parsing behavior against a real room-state event from the dev homeserver.
