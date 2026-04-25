---
title: Frontend Merger and Shell Plan
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 003
migrated_from:
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/README.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/VERIFY-GATES.md
  - specs/execution/archive/exec-merge-chat-SUPERSEDED.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
adrs: []
---

# Plan

## Architecture

`frontend_merger/` is the canonical shell for user-facing web surfaces. It owns
routing, shared top navigation, frontend build/test gates and shell-level live
smoke across Matrix, Agent, Control, Files and Memory.

## Critical Files

- `frontend_merger/src/app/*`
- `frontend_merger/src/components/GlobalTopBar.tsx`
- `frontend_merger/src/features/*`
- `frontend_merger/tests/*`
- `frontend_merger/package.json`
- `frontend_merger/next.config.*`

## Migration Strategy

1. Treat branch execs as implementation evidence.
2. Treat `exec-merge-chat-SUPERSEDED` as design history only.
3. Split A2UI-specific work to Feature 008.
4. Keep shell, route, build and page-smoke work here.

## Risks

- Shell live smoke passing while individual feature backends are broken.
- Route consolidation being treated as functional work when it is mostly UX.

