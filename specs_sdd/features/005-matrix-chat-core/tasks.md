---
title: Matrix Chat Core Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 005
migrated_from:
  - specs/execution/exec2-04-verify-gates.md
---

# Tasks

- [x] T001 Import `exec2-04` sections A-O into `live-verify.md`.
- [x] T002 Preserve `exec2-04` A-O gate groups in `gates.md`.
- [x] T003 Mark each Matrix gate group as active, blocked external, superseded, moved or done.
- [x] T004 Summarize archived feature/review/refactor docs in `closeout.md`.
- [x] T005 [P] Verify static build includes `/matrix`.
- T006 Verify Matrix login, room list and timeline with local homeserver.
- T007 Verify send/receive/edit/react/redact basics.
- T008 Verify E2EE/device state or record external blocker.
- T009 Verify uploads/media and queue behavior.
- T010 Verify calls/MatrixRTC if in current scope.
- T011 Verify advanced options/onboarding where not blocked.

## Verify Gates

- [x] Browser route builds as `/matrix`; browser render smoke deferred.
- Protocol session works.
- E2EE state is tested or blocked with reason.
- [x] `exec2-04` no longer contains uncategorized gate groups.
