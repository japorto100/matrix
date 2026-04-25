---
title: Matrix Chat Core Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 005
migrated_from:
  - specs/execution/exec2-04-verify-gates.md
---

# Live Verify

The detailed legacy gate ledger is in `gates.md`. This file is the executable
run sheet. Gate IDs below refer to `gates.md`.

## A. Infrastructure

- Tuwunel reachable.
- Matrix client config loaded.
- Browser route `/matrix` renders without crash.
- A1-A4 gate status recorded.

## B. Auth + E2EE

- Login works.
- Device/session state visible.
- E2EE room can be opened or blocker documented.
- Key backup/cross-signing gates classified.
- B1-B4 gate status recorded.

## C. Chat Core

- Room list loads.
- Timeline loads.
- Send plain text.
- Receive plain text from second client or bot.
- Edit message.
- React to message.
- Redact/delete message.
- Read receipt / unread state behaves correctly.
- C1-C8 gate status recorded.

## D. Advanced Messaging

- Threads.
- Polls.
- Mentions.
- Reply/quote if implemented.
- Spaces/widgets if in scope.
- D0-D3 gate status recorded.

## E. Composer

- WYSIWYG/Tiptap editor basic input.
- Markdown/plain fallback.
- Keyboard shortcuts.
- Error/retry state.
- E gate status recorded.

## F. Media and Uploads

- Image upload.
- File upload.
- Upload progress.
- Retry failed upload.
- Preview/download.

## G. Calls

- Incoming call UI.
- Outgoing call UI.
- Mute/camera toggles.
- Hangup state.
- MatrixRTC/LiveKit blocker documented if not testable.
- F1-F6 gate status recorded.

## H. Mobile / Connectivity

- Element X discovery if mobile scope active.
- Tunnel path works if mobile scope active.
- Federation path classified as enabled, disabled or deferred.
- I/J/K gate status recorded or moved to Feature 004.

## I. Cinny / SOTA Gates

- Cinny integration gates classified.
- Phase 2/3 Cinny gates marked done, skipped or active.
- No old Cinny gate remains uncategorized.
- L/M/N gate status recorded.
- O architecture decisions linked to Feature 006 and Feature 009 where applicable.

## Result

pending
