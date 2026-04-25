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

- [ ] Go appservice starts and registers.
- [ ] Python bridge starts and subscribes.
- [ ] Go publishes inbound event.
- [ ] Python consumes inbound and calls agent service.
- [ ] Python publishes reply.
- [ ] Go consumes reply and sends Matrix message.
- [ ] No legacy Python Matrix sync loop is active.

## G2 E2EE Path

- [ ] `MATRIX_E2EE_ENABLED=true` path runs.
- [ ] Go decrypts encrypted inbound event.
- [ ] Go encrypts response in E2EE room.
- [ ] Cross-Signing state is valid.
- [ ] Key Backup survives restart.
- [ ] Client key-sharing behavior is verified or blocker documented.

## G3 Routing / Isolation

- [ ] Mention routes to expected target agent.
- [ ] DM to agent can resolve target without body regex or legacy fallback is
  documented.
- [ ] Subject routing fallback and enabled modes are tested.
- [ ] NATS authorization gap is closed or explicitly deferred.
- [ ] Thread replies preserve thread metadata.

## G4 Key Deletion / Hybrid

- [ ] Delete-after-decrypt true path redacts keys.
- [ ] Delete-after-decrypt false path keeps keys.
- [ ] `gateway` capability keeps current decrypt behavior.
- [ ] `native` capability is marked interface-only until real ciphertext
  forwarding exists.

## G5 Future Bridge Classification

- [ ] WhatsApp/Signal/Telegram/Meta/Discord bridge work is backlog unless
  promoted.
- [ ] Hookshot/maubot/feed bridge work is routed to integration/ingestion
  backlog.
- [ ] Content-ingestion sections are owned by memory/ingestion features, not
  this feature's closeout.
