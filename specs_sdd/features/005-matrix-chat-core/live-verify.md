---
title: Matrix Chat Core Live Verify
status: partial-api-live
owner: filip
created: 2026-04-25
updated: 2026-04-29
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

partial API live pass; browser render and richer chat interactions remain open.

## API Evidence 2026-04-27

- Tuwunel was reachable on `http://localhost:8448`.
- A fresh `@codex-smoke-*` user was registered with the current
  `matrix-dev-token-2026` registration token.
- The smoke user created room `!XG1qUg2zlFAr-infXHNYwKYHnNmUtO7yWg7HbXQov0Q`.
- Plain-text send returned event `$g21dzH-_fzspnqlhJnDTz8bSxICFaW3GwZ5VmtSoxYs`.
- `/sync?timeout=0` returned `timeline_found=1` for that event.

Not covered in this pass:

- Browser `/matrix` render.
- Existing `@alice`/`@bob` dev credential recovery.
- Edit, reaction, redact, second-client receive, media, calls and E2EE.

## Static Evidence 2026-04-29 — Matrix Widget Surface

Status: pass for resolver/render safety; live room-state/browser interop remains
open.

Evidence:

- `resolveMessage` now normalizes `m.widget` and `im.vector.modular.widgets`
  events into `msgType="m.widget"` with `url` set only for `http/https`.
- `MessageBubble` renders safe widget URLs as external links with
  `rel="noopener noreferrer"` and does not embed arbitrary iframe content.
- Unsafe widget URLs such as `javascript:` render as passive text with a blocked
  marker.
- Focused frontend checks:
  `cd frontend_merger && bunx vitest run src/features/matrix/lib/resolvers.test.ts src/features/matrix/components/message/MessageContent.test.tsx`
  => `2 passed`, `4 passed`.
- Frontend typecheck:
  `cd frontend_merger && bun run typecheck` => pass.
