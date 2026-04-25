---
title: Frontend Merger and Shell Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 003
migrated_from:
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/README.md
  - specs/execution/claude-merge-frontend-chat-ui-2OqmH/VERIFY-GATES.md
  - docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
---

# Tasks

- [x] T001 Summarize branch exec build/lint/test evidence in `closeout.md`.
- [x] T002 [P] Run or record latest frontend build -> `frontend_merger/`.
- [x] T003 [P] Run or record frontend unit/E2E smoke -> `frontend_merger/tests/`.
- [x] T004 Verify shell routes: `/`, `/matrix`, `/control`, `/files`, `/memory`.
- [x] T005 Split plan-v2 open items #93/#94/#95 to Feature 008 or route UX backlog.
- [x] T006 Document route consolidation decision as deferred unless chosen.
- T007 Add shell-level live verify evidence. Deferred by current work order.

## Verify Gates

- [x] Frontend build passes.
- [x] Frontend typecheck/lint passes or known pre-existing issues are listed.
- Route smoke returns non-error pages for all shell surfaces. Deferred to
  live/browser verify.
