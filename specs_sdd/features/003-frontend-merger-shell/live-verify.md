---
title: Frontend Merger and Shell Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 003
---

# Live Verify

## Required Flows

- Open `/` and confirm the shell renders.
- Open `/matrix` and confirm Matrix surface renders a valid state.
- Open `/control` and confirm Control UI shell renders.
- Open `/files` and confirm Files surface renders.
- Open `/memory` and confirm Memory surface renders.
- Open the global Agent Chat overlay from the shell and confirm it renders.
- Open `/control/agents` and confirm Agent configuration renders.
- Use GlobalTopBar navigation between all surfaces without full-page errors.
- Confirm missing env values produce actionable empty/config states, not crashes.

## Evidence

- Browser screenshots or Playwright trace for each route.
- Console error summary.

## Result

pending
