---
title: Matrix Chat Core Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-29
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
- T006 [partial-live-api] Verify Matrix login, room list and timeline with local homeserver.
  - 2026-04-27: fresh `@codex-smoke-*` user registered through Tuwunel,
    created a room and `/sync?timeout=0` returned the sent event in the
    timeline. Browser route/render remains out of this pass.
- T007 [partial-live-api] Verify send/receive/edit/react/redact basics.
  - 2026-04-27: plain-text send over Matrix Client-Server API succeeded.
    Edit/react/redact and second-client receive remain open.
- T008 Verify E2EE/device state or record external blocker.
- T009 Verify uploads/media and queue behavior.
- T010 Verify calls/MatrixRTC if in current scope.
- T011 Verify advanced options/onboarding where not blocked.
- [x] T012 Static-harden Matrix widget events (`m.widget` /
  `im.vector.modular.widgets`): preserve safe `http/https` URLs, block
  `javascript:`/non-web URLs and render a link card instead of embedding an
  arbitrary iframe.

## Verify Gates

- [x] Browser route builds as `/matrix`; browser render smoke deferred.
- [x] Protocol session works for login/register, room create, send and timeline
  sync through the Matrix Client-Server API.
- [x] Widget state events resolve safely and do not create inline iframe
  execution in the chat timeline.
- E2EE state is tested or blocked with reason.
- [x] `exec2-04` no longer contains uncategorized gate groups.
