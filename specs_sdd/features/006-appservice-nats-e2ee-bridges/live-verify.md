---
title: Appservice, NATS, E2EE and Bridges Live Verify
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
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

pending
