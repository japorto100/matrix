---
title: Appservice, NATS, E2EE and Bridges Tasks
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 006
migrated_from:
  - specs/execution/exec-05-nats-e2ee-pipeline.md
  - specs/execution/exec-05b-messaging-bridges.md
  - specs/execution/exec-05c-agent-isolation.md
---

# Tasks

## Migration / SDD

- [x] T001 Summarize implemented exec-05 phases in SDD current state.
- [x] T002 Split exec-05b messaging bridges into future/backlog, not active
  closure criteria.
- [x] T003 Split exec-05c isolation into built-disabled, open and research
  states.
- [x] T004 Preserve E2BE, key deletion, hybrid E2EE and NATS-vs-HTTP/LiveKit
  decisions.

## Core Gateway

- [x] T010 Run Go build/tests with `goolm`/E2EE tags where applicable
  (`go test -tags goolm ./...`).
- T011 Verify appservice registration handshake with homeserver.
- T012 Verify Go message filter: DMs always forward; groups forward only
  mention/reply/trigger where `MENTION_ONLY_IN_GROUPS=true`.
- T013 Verify Go publishes inbound event on `matrix.message.inbound`.
- T014 Verify Python NATS subscriber consumes inbound message and calls agent
  HTTP/SSE endpoint.
- T015 Verify Python publishes reply on `matrix.message.reply`.
- T016 Verify Go receives reply and sends Matrix message as agent intent.
- [x] T017 Add/static-test Python reply thread metadata propagation from
  inbound `thread_id` to reply `thread_root_id`.
- [x] T018 Static-lint Python bridge/agent/voice code with ruff.

## E2EE

- T020 Execute A4 unencrypted E2E handoff test.
- T021 Execute encrypted room E2E handoff test.
- T022 Verify Go decrypts `m.room.encrypted` event.
- T023 Verify Go encrypts response in E2EE room.
- T024 Verify Cross-Signing seeds/device signature exist after bot startup.
- T025 Verify Key Backup restart: old messages still readable when deletion
  disabled.
- T026 Verify `NEXT_PUBLIC_E2EE_BLACKLIST_UNVERIFIED` dev/prod semantics are
  documented and current.

## Isolation / Routing

- [x] T030 Verify `NATS_SUBJECT_ROUTING_ENABLED=false` fallback uses global
  subjects by code inspection/default config.
- T031 Live-verify enabled subject routing emits
  `matrix.message.inbound.room.*` or `.agent.*` as designed.
- [x] T032 Implement/static-test Python enabled subject-routing subscription:
  bridge subscribes to both `matrix.message.inbound` and
  `matrix.message.inbound.>`.
- [x] T033 Implement/verify NATS authorization so an agent can read only allowed
  subjects.
- [x] T034 Static-test thread support: inbound thread metadata is forwarded into
  the reply payload.
- [x] T035 Static-test dynamic reply user-id from `target_agent`.

## Key Deletion / Hybrid E2EE

- T040 Verify `MATRIX_DELETE_KEYS_AFTER_DECRYPT=false` keeps keys.
- T041 Verify `MATRIX_DELETE_KEYS_AFTER_DECRYPT=true` redacts group session
  after decrypt.
- T042 Decide whether `MATRIX_DELETE_KEYS_AFTER_HOURS` needs implementation
  before production.
- T043 Verify `MATRIX_AGENT_CAPABILITIES=gateway` keeps current behavior.
- T044 Mark `native` capability as interface-only until ciphertext forwarding
  and vodozemac-python are implemented.
- T045 Evaluate vodozemac-python and Soatok 2026 crypto notes before native
  per-agent E2EE.

## Future Bridges

- [x] T050 Keep WhatsApp and Signal bridges as Priority-1 backlog after core
  Matrix E2EE live verify.
- [x] T051 Keep Telegram, Meta and Discord as Priority-2/3 backlog.
- [x] T052 Classify Hookshot/maubot/RSS and non-Messenger bridges as ingestion
  or integration backlog, not Feature 006 closure work.
- [x] T053 Move content ingestion sections to Feature 012/010 backlog where
  appropriate.

## Verify Gates

- Go appservice starts.
- NATS message path works.
- Encrypted Matrix message can traverse appservice -> NATS -> Python.
- Reply path works or is explicitly deferred.
- Subject isolation/key deletion are verified or clearly deferred.
