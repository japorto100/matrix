---
title: Control UI and Runtime Surfaces Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 010
---

# Closeout

## Built

- `/control/[[...tab]]` route and Control shell in `frontend_merger`.
- Top-level Control tab dispatch for overview, agents, permissions, skills,
  tools, sandbox, sessions, system, audit, MCP, A2A, security, context, tasks
  and models surfaces.
- Catch-all `/api/control/[...path]` BFF proxy to the Go/Python control backend.
- Typed React Query clients for Control, Memory and Scheduler surfaces.
- Explicit mock fallback pattern through `mock-data.ts`.

## Not Built

- Tab-by-tab live evidence that each surface has real backend data, actionable
  empty state or owning-feature gap.
- Proven upload/preview/reindex flow through storage.
- Proven Control BFF header/body/query preservation.
- Removal/labeling of every mock fallback in live mode.

## Deviations From Plan

- The old standalone `control-ui/` concept is superseded by `frontend_merger`.
- Control is an integration cockpit. Its backend gaps close in owner features
  011-015 instead of being solved wholesale in Feature 010.

## Verify Result

- PASS static: frontend lint/typecheck/test/build gates passed in the shared
  frontend verification.
- PASS static: route, BFF proxy and query-client surfaces exist.

## Live Verify Result

Pending tab-by-tab walkthrough.

## Follow-Ups

- Run browser walkthrough for every tab and record live/mock/broken state.
- Route backend gaps to owner features: 011 models/billing, 012 memory/KG,
  013 sandbox/security, 014 observability, 015 skills/scheduler.
- Keep mock fallbacks only where the UI clearly communicates backend absence or
  deferred scope.
