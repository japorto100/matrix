---
title: Appservice, NATS, E2EE and Bridges Live Verify
status: unencrypted-live-pass-e2ee-open
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

unencrypted live Matrix handoff pass; Feature 006 is not closed because
encrypted-room, key backup, cross-signing and key-deletion gates remain open.

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
- 2026-04-27 follow-up: Tuwunel and Garage were started and
  `/_matrix/client/versions` plus local `.well-known` passed. Persisted
  `@alice`/`@bob` credentials were recovered through Tuwunel admin recovery,
  `scripts/setup-users.sh` succeeded, and `scripts/register-appservice.sh`
  accepted the admin token/password fallback.
- E2EE decrypt/encrypt, cross-signing, key backup and key deletion gates remain
  open.

## Full Unencrypted Evidence 2026-04-27

- Stack status was green for `tuwunel`, `go-appservice`, `nats`,
  `python-bridge`, `python-agent`, `postgres`, `valkey`, `garage`,
  `litellm`, `sandbox` and `python-ingestion`.
- Appservice health returned `{"status":"ok","service":"matrix-appservice",
  "e2ee":"disabled"}`.
- `scripts/register-appservice.sh` registered `trading-agent` after validating
  Alice admin credentials.
- Matrix Client API smoke created a private room, invited
  `@agent-alice:matrix.local`, sent an Alice message, observed Go publish the
  inbound event to NATS, let Python bridge/agent publish the reply, and then
  found the reply in Matrix sync:
  - `room_id`: `!q9zBX-Woqjq6SDFPfOEjWNV6m37zCgfTxgO6ui4rafk`
  - `sent_event_id`: `$SO7kCxRFEyx6ZRy2JfTT5qYTnYY3SLxt2r4DEoFuVNE`
  - `agent_reply_found`: `true`
  - `agent_reply.event_id`: `$bqofG3Xk3-J0eq7arExjtwTdHj4RDWAy9HPNxHH52C4`
- Bugs fixed during this pass:
  - Go appservice now includes Matrix transaction IDs when sending agent
    messages, avoiding `/_send/.../` 404s.
  - Go appservice resolves DM replies to the joined room agent when no explicit
    `@agent-*` mention exists, avoiding `@agent-bot` membership `M_FORBIDDEN`.
  - Python Bridge now parses AI-SDK-v6 `text-delta`/`delta` packets as well as
    the legacy `text_delta`/`text` shape.
  - Agent HTTP entry now honors `AGENT_DEFAULT_UTILITY_MODEL` when no
    control-ui user model is selected, and development can use provider ENV
    credentials when no per-user DB key is seeded.
  - Python Bridge forwards the Matrix sender as `x-auth-user` so per-user model
    and credential lookup can work for Matrix traffic.
- Second full live proof used the real Python Agent/OpenRouter path, not a
  manual NATS reply:
  - `room_id`: `!whDYMsaAvmfYe_DAuHoAO9GdXITGGtjMuNoDSBmpkKg`
  - `sent_event_id`: `$R8EnzPOnRY96Oh73U3N62mS5wUb2zPtmG2p7DT57YoY`
  - `agent_reply_found`: `true`
  - `agent_reply.event_id`: `$EdKTt1gKWBvMqyPbd1uZis9q6D73vqw-oERjt09myjk`
  - `agent_reply.body`: `matrix parser fixed`

## 2026-04-30 Added Live Gates

- LV030 Restart appservice/NATS during an active room session and verify event
  id dedupe prevents duplicate replies.
- LV031 Verify encrypted media/event failure surfaces E2EE bootstrap status
  instead of silent cleartext fallback.
- LV032 Verify approval reactions carry room id, event id, thread id and actor
  identity through bridge trace metadata.
- LV033 Verify bridge health exposes transport, crypto and queue state
  separately in Control/Ops events.
