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

- [ ] T001 Classify `exec-blocking` C1-C6 as external blocked, local task or resolved.
- [ ] T002 Document current homeserver version and config baseline.
- [ ] T003 Verify Tuwunel compose startup under current profile.
- [ ] T004 Verify connectivity/tunnel path selected for local mobile testing.
- [ ] T005 Verify `.well-known/matrix/client` when mobile scope is active.
- [ ] T006 Record OIDC/MAS/federation status and next review date.
- [ ] T007 Move historical Dendrite fallback notes into research/history if stale.

## Verify Gates

- [ ] Homeserver starts.
- [ ] Client discovery works when configured.
- [ ] External blockers have owner/status/date.

