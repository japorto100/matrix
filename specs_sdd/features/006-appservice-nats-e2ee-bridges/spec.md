---
title: Appservice, NATS, E2EE and Bridges
status: static_verified_live_pending
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 006
migrated_from:
  - specs/02-go-appservice.md
  - specs/03-python-agent-bridge.md
  - specs/06-e2ee.md
  - specs/13-e2ee-agent-architecture.md
  - specs/execution/exec-05-nats-e2ee-pipeline.md
  - specs/execution/exec-05b-messaging-bridges.md
  - specs/execution/exec-05c-agent-isolation.md
adrs: []
---

# Appservice, NATS, E2EE and Bridges

## Current State / Ist

Go appservice, Python bridge and the NATS E2EE pipeline are code-complete for
the core architecture: Go is the single Matrix crypto gateway, Python no longer
uses `matrix-nio`, Go publishes decrypted inbound events to NATS and receives
Python replies on NATS, and goolm-backed E2EE/Cross-Signing/Key-Backup support
exists.

But the old execution files do not close the slice: `exec-05` still marks A4
end-to-end Matrix -> Go -> NATS -> Python -> NATS -> Go -> Matrix as pending,
and the E2EE gate still needs live proof that encrypted messages decrypt and
encrypted replies reach the client. `exec-05c` added subject routing, agent
routing, thread support, key deletion flags and hybrid-interface scaffolding,
but subject routing is default-disabled, Python currently subscribes to the
global inbound subject only, and NATS authorization is still open. `exec-05b`
is planned future bridge scope, not current built state.

Static verification on 2026-04-25 passed the Go appservice test suite with the
`goolm` tag, Python bridge/agent tests for NATS thread replies and A2UI
streaming, and Python lint for bridge/agent/voice code. One implementation gap
was closed during this SDD pass: inbound NATS `thread_id` is now forwarded as
reply `thread_root_id`, so Matrix threaded replies can keep their root event
metadata when the live path is exercised.

## Target State / Soll

The appservice is the single Matrix crypto gateway, NATS is the internal
message bus for Matrix event handoff, and Python agents receive/send through a
tested, observable handoff. Agent Chat and Voice do not use NATS for token/voice
streaming; they use HTTP/SSE and LiveKit respectively.

## Subfeatures

- 006.1 Go appservice Matrix/E2EE gateway
- 006.2 Python NATS bridge and agent-client handoff
- 006.3 NATS subject routing, agent routing and thread support
- 006.4 E2EE trust model, key backup and key deletion policy
- 006.5 Appservice namespaces and agent sender identities
- 006.6 Future messaging bridges and E2BE bridge pattern
- 006.7 Hybrid/per-agent E2EE evaluation
- 006.8 Production transport hardening: JetStream, TLS, NATS authorization

## Gap

- A4 end-to-end live test is the main closure blocker.
- E2EE live proof is still needed: encrypted inbound decrypt, encrypted reply,
  Cross-Signing, key backup restart behavior.
- NATS authorization for per-agent isolation is not implemented.
- Subject routing exists behind `NATS_SUBJECT_ROUTING_ENABLED=false`; Python now
  subscribes to both the global inbound subject and routed
  `matrix.message.inbound.>` subjects. Live routing still needs proof with Go
  publishing enabled.
- Key deletion is implemented as a config path, but live key-retention/deletion
  behavior is unverified.
- Future messaging bridges stay backlog/research until exec-05 A/B are
  live-verified.
- vodozemac-python / per-agent native E2EE remains research, not active scope.

## Static Verify

- [x] `go test -tags goolm ./...` passes in `go-appservice`.
- [x] `uv run pytest tests/bridge/test_nats_handler.py tests/agent/test_streaming_a2ui.py -q` passes in `python-backend`.
- [x] `uv run ruff check bridge tests/bridge agent voice` passes in `python-backend`.
- [x] Thread reply metadata is covered by `tests/bridge/test_nats_handler.py`.
- [x] Future bridges are classified as backlog, not current done work.

## Live Verify

- Go appservice starts with current config.
- Python subscriber receives NATS message.
- End-to-end encrypted Matrix message can cross the gateway.
- Reply path sends as expected agent identity.
- Isolation/key-deletion behavior is either verified or explicitly deferred.

## Closeout Criteria

- `exec-05*` files are summarized into task/live-verify state.
- Bridges that are not current Matrix scope are moved to research/backlog.
