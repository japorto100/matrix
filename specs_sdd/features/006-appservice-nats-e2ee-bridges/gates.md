---
title: Appservice NATS E2EE Bridges Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-30
feature_id: 006
---

# Gates

## G1 Core NATS Path

- [x] Go appservice static tests pass with `go test -tags goolm ./...`.
- [x] Go appservice starts and registers.
- [x] Python bridge starts and subscribes.
- [x] Go publishes inbound event.
- [x] Python consumes inbound and calls agent service.
- [x] Python publishes reply.
- [x] Go consumes reply and sends Matrix message in unencrypted live rooms.
- [x] Python bridge/A2UI static tests pass.
- [x] No legacy Python Matrix sync loop is in the current bridge path.
- [x] Matrix echo/pairing-loop guard is tested against self-sent or reflected
  appservice events.
- [partial] Mention/thread rules are tested for DM, group mention and free-response
  room cases. Python bridge rejects malformed thread replies without a root and
  preserves thread metadata; Go group-room free-response allowlist/live cases
  remain open.
- [ ] Reaction-based approvals, if enabled, bind to the correct Matrix room,
  event and agent session.
- [partial] Reconnect/session replay does not duplicate replies or lose
  in-flight approval state. Python bridge dedupes repeated `event_id`; live
  reconnect and approval state replay remain open.

## G2 E2EE Path

- [ ] `MATRIX_E2EE_ENABLED=true` path runs.
- [ ] Go decrypts encrypted inbound event.
- [ ] Go encrypts response in E2EE room.
- [ ] Cross-Signing state is valid.
- [ ] Cross-signing/bootstrap failure is visible as a blocker with remediation.
- [ ] Key Backup survives restart.
- [ ] Client key-sharing behavior is verified or blocker documented.

## G3 Routing / Isolation

- [x] `target_agent` maps to expected reply Matrix user id in Python bridge
  test.
- [x] DM to agent can resolve target without body regex or legacy fallback.
- [x] Subject routing fallback is the default static config.
- [x] Python subscribes to routed inbound subjects.
- [ ] Subject routing enabled mode is live-verified end-to-end with Go publish.
- [x] NATS authorization gap is explicitly deferred.
- [x] Thread replies preserve thread metadata in reply payload tests.

## G4 Key Deletion / Hybrid

- [ ] Delete-after-decrypt true path redacts keys.
- [ ] Delete-after-decrypt false path keeps keys.
- [ ] `gateway` capability keeps current decrypt behavior.
- [ ] `native` capability is marked interface-only until real ciphertext
  forwarding exists.

## G5 Future Bridge Classification

- [x] WhatsApp/Signal/Telegram/Meta/Discord bridge work is backlog unless
  promoted.
- [x] Hookshot/maubot/feed bridge work is routed to integration/ingestion
  backlog.
- [x] Content-ingestion sections are owned by memory/ingestion features, not
  this feature's closeout.

## 2026-04-30 Added Gates

- [ ] E2EE missing dependency/state fails loudly instead of silently
  downgrading encrypted rooms.
- [ ] Device verification, room-key backup and recovery-key restore are
  individually visible.
- [ ] Encrypted media produces a decrypted local file path only after policy
  and crypto checks pass.
- [ ] Bot-to-bot and self-loop suppression happen before agent execution.
