---
title: Appservice, NATS, E2EE and Bridges Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 006
---

# Live Verify

## Source Checks

- `exec-05` A4 is still treated as open until tested.
- `exec-05b` bridges are backlog/future, not implemented status.
- `exec-05c` built-disabled/open/research split is represented.
- `06-e2ee.md` and `13-e2ee-agent-architecture.md` trust model matches SDD.

## Required Flows

- Start homeserver, appservice, NATS and Python backend.
- Confirm appservice registration is accepted.
- Send Matrix message from browser/client to appservice-managed room.
- Confirm Go receives event.
- Confirm Go decrypts or handles encrypted payload according to E2EE mode.
- Confirm NATS publish on expected subject.
- Confirm Python bridge consumes message.
- Confirm agent response or mock response publishes reply.
- Confirm reply reaches Matrix room.
- Confirm reply uses expected agent identity.

## E2EE Checks

- Repeat required flow in encrypted room.
- Confirm Go decrypts `m.room.encrypted`.
- Confirm Go encrypts response in encrypted room.
- Verify Cross-Signing device state or record blocker.
- Restart Go appservice and verify key backup behavior.

## Isolation / Bridge Checks

- Agent-specific NATS routing works or is disabled intentionally.
- Key deletion behavior is documented.
- External messaging bridges are not enabled without explicit scope.
- NATS authorization gap is closed or explicitly deferred.

## Result

partial backend-only pass; Feature 006 is not closed.

## Backend-Only Evidence 2026-04-27

- `./scripts/dev-stack.sh --go` started Go appservice locally after Matrix-local
  NATS/Postgres/Python services were already running.
- `GET http://127.0.0.1:29318/health` returned `200` with service
  `matrix-appservice`; logs show NATS connected to `nats://localhost:14222` and
  subscribed to `matrix.message.reply`.
- Synthetic NATS publish to `matrix.message.inbound` produced a reply on
  `matrix.message.reply`:
  - `room_id`: `!backend-smoke:matrix.local`
  - `agent_user_id`: `@agent-trading:matrix.local`
  - `thread_root_id`: `$thread-smoke`
- Python bridge logs show inbound consumption, Agent HTTP/SSE call to
  `http://localhost:8094/api/v1/agent/chat`, and reply publish.
- Go appservice logs show it received the reply and attempted a threaded Matrix
  send as `@agent-trading:matrix.local`.

Remaining full-live blockers:

- This was not a "without stack" test. It used a real partial stack:
  `matrix-nats`, `python-bridge`, `python-agent`, `go-appservice` and
  Postgres. It did not use Tuwunel or a real Matrix client.
- 2026-04-27 follow-up: Tuwunel and Garage were started and `/_matrix/client/versions`
  plus local `.well-known` passed. Appservice registration still did not close:
  `scripts/register-appservice.sh` failed because existing persisted
  `@alice:matrix.local` rejects the expected dev password, and
  `scripts/setup-users.sh` now exits nonzero when bootstrap/login fails.
- Final Matrix room delivery still needs Tuwunel plus a real room/client.
- E2EE decrypt/encrypt, cross-signing, key backup and key deletion gates remain
  open.
