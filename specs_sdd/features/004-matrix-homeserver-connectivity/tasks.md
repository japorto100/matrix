---
title: Matrix Homeserver, Connectivity and Mobile/Federation Tasks
status: partial-local-live
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
- [x] T003 [done-live-partial] Verify Tuwunel startup under current profile.
  - 2026-04-27: `tuwunel` and `garage` were started from existing Matrix
    containers; `GET /_matrix/client/versions` returned supported versions.
    `./scripts/dev-stack.sh --tuwunel --storage=garage` still has an
    orchestration/start-order issue and timed out before manual `podman start`
    recovered both services.
- [x] T004 Verify connectivity/tunnel path selected for local mobile testing.
- T005 [partial-live-local] Verify `.well-known/matrix/client` when mobile scope is active.
  - 2026-04-27: local `GET /.well-known/matrix/client` returned homeserver
    `http://localhost:8448/` and MatrixRTC LiveKit focus metadata. LAN/mobile
    discovery and tunnel URL remain live/mobile gates.
- [x] T006 Record OIDC/MAS/federation status and next review date.
- [x] T007 Move historical Dendrite fallback notes into research/history if stale.

## Verify Gates

- [x] Homeserver starts locally; devstack compose start-order still needs follow-up.
- [x] Client discovery works locally; LAN/mobile/tunnel discovery remains deferred.
- [x] External blockers have owner/status/date.

## 2026-04-30 OpenClaw Matrix QA Additions

- T008 Add disposable Tuwunel QA lane plan with driver, SUT and observer
  users, private room setup, hard timeout and cleanup recovery command.
- T009 Add account-scoped Matrix credential/state diagnostics for default and
  named accounts.
- T010 Add E2EE startup verification and backup status as connectivity gates.
