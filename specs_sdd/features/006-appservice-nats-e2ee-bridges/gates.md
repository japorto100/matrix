---
title: Appservice NATS E2EE Bridges Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 006
---

# Gates

## G1 Core NATS Path

- [x] Go appservice static tests pass with `go test -tags goolm ./...`.
- [ ] Go appservice starts and registers. Starts locally; registration remains
  blocked by stale Tuwunel dev credentials for the admin-command path.
- [x] Python bridge starts and subscribes.
- [ ] Go publishes inbound event.
- [x] Python consumes inbound and calls agent service.
- [x] Python publishes reply.
- [ ] Go consumes reply and sends Matrix message. Go consumed the synthetic
  reply and attempted Matrix send; final room delivery remains blocked until
  appservice registration and a real Matrix room are verified.
- [x] Python bridge/A2UI static tests pass.
- [x] No legacy Python Matrix sync loop is in the current bridge path.

## G2 E2EE Path

- [ ] `MATRIX_E2EE_ENABLED=true` path runs.
- [ ] Go decrypts encrypted inbound event.
- [ ] Go encrypts response in E2EE room.
- [ ] Cross-Signing state is valid.
- [ ] Key Backup survives restart.
- [ ] Client key-sharing behavior is verified or blocker documented.

## G3 Routing / Isolation

- [x] `target_agent` maps to expected reply Matrix user id in Python bridge
  test.
- [ ] DM to agent can resolve target without body regex or legacy fallback is
  documented.
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
