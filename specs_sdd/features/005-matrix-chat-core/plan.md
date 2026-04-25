---
title: Matrix Chat Core Plan
status: draft
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
adrs: []
---

# Plan

## Architecture

Matrix Chat lives in `frontend_merger` and depends on Feature 004 for
homeserver/connectivity and Feature 006 for appservice/E2EE handoff.

## Critical Files

- `frontend_merger/src/features/matrix/**`
- Matrix route files under `frontend_merger/src/app/**`
- Matrix SDK configuration
- Tests under `frontend_merger/tests/**`
- `go-appservice/internal/**` only where Matrix UI verify crosses gateway

## Migration Strategy

1. Split old `exec2-04` gates into live-verify sections.
2. Treat old archived UI/review docs as history, not task source.
3. Keep Cinny verification as closeout evidence.
4. Put externally blocked items in Feature 004.

## Risks

- Counting automated render smoke as Matrix protocol verification.
- Keeping stale old feature wishlists as active tasks.

