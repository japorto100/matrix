---
title: Matrix Chat Core
status: implementation_done
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 005
migrated_from:
  - specs/04-nextjs-chat.md
  - specs/execution/exec2-01-matrix-chat-core.md
  - specs/execution/exec2-02-protocol-infra.md
  - specs/execution/exec2-03-ui-rework-sota.md
  - specs/execution/exec2-03b-advanced-matrix-options.md
  - specs/execution/exec2-03c-cinny.md
  - specs/execution/exec2-04-verify-gates.md
  - specs/execution/archive/exec-02-missing-features.md
  - specs/execution/archive/exec-03-review-fixes.md
  - specs/execution/archive/exec-04-ui-rework.md
  - specs/execution/archive/exec-07-refactoring.md
adrs: []
---

# Matrix Chat Core

## Current State / Ist

Matrix chat has substantial implemented history across original specs, archived
review/fix slices and `exec2-*`. Cinny integration has a `sota-verify PASS`.
`exec2-04` is the broad verify-gate ledger. Some gates are implemented, some
are external-blocked, and live room/timeline/E2EE/call checks still need a real
stack.

The current static pass confirmed that `/matrix` is part of the successful
`frontend_merger` Turbopack production build. `exec2-04` gate groups A-O are
preserved in `gates.md` and classified by ownership/status.

## Target State / Soll

Matrix chat in `frontend_merger` is the canonical Matrix UI. It supports the
core room and timeline flows, E2EE expectations, media/upload/call features,
advanced options and clear live verify gates.

## Subfeatures

- Room list and timeline
- Composer, edits, reactions, redactions
- Threads, polls, spaces and widgets
- Media and upload queue
- Browser E2EE and device trust
- Calls and MatrixRTC/LiveKit surfaces
- Cinny reuse/integration
- Advanced server/onboarding options
- Matrix verify-gate ledger

## Gap

- Run full-stack live Matrix session.
- Browser route smoke, protocol session, E2EE and calls remain live-gated.
- Feature 004 owns homeserver/connectivity/mobile/federation gates.

## Verify

- [x] `/matrix` static build route exists.
- Matrix login and room list.
- Send/receive text.
- E2EE handshake or documented blocked reason.
- Upload/media path.
- Calls path if in current scope.

## Closeout Criteria

- Historical execs are not used as task sources.
- `live-verify.md` records the real Matrix stack run.
