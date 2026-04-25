---
title: Matrix Homeserver, Connectivity and Mobile/Federation Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 004
migrated_from:
  - specs/execution/exec-matrix-monitor.md
  - specs/execution/exec-blocking.md
---

# Tasks

- [x] T001 Classify `exec-blocking` C1-C6 as external blocked, local task or resolved.
- [x] T002 Document current homeserver version and config baseline.
- T003 Verify Tuwunel compose startup under current profile. Deferred to live/operator verify.
- [x] T004 Verify connectivity/tunnel path selected for local mobile testing.
- T005 Verify `.well-known/matrix/client` when mobile scope is active. Deferred to live/mobile verify.
- [x] T006 Record OIDC/MAS/federation status and next review date.
- [x] T007 Move historical Dendrite fallback notes into research/history if stale.

## Verify Gates

- Homeserver starts. Deferred to live/operator verify.
- Client discovery works when configured. Deferred to live/mobile verify.
- [x] External blockers have owner/status/date.
