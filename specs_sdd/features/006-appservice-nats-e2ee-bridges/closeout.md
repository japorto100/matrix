---
title: Appservice, NATS, E2EE and Bridges Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 006
---

# Closeout

## Built

- Go appservice core NATS bridge and E2EE gateway code are present.
- Python bridge consumes the global inbound subject and publishes replies.
- Python bridge also subscribes to routed inbound subjects
  `matrix.message.inbound.>` for enabled subject-routing mode.
- Dynamic reply identity from `target_agent` is implemented and covered by a
  Python bridge test.
- Thread metadata propagation from inbound `thread_id` to reply
  `thread_root_id` is implemented and covered by a Python bridge test.
- Future messaging bridge scope is classified as backlog/research rather than
  Feature 006 closure work.

## Not Built

- NATS per-agent authorization.
- Native per-agent E2EE/ciphertext forwarding.
- WhatsApp/Signal/Telegram/Meta/Discord bridge implementations.

## Deviations From Plan

- Agent Chat and Voice streaming remain outside NATS by design; they use
  HTTP/SSE and LiveKit paths.
- `NATS_SUBJECT_ROUTING_ENABLED=false` remains the safe default. Enabled mode
  now has Python subscription support, but still needs live proof and NATS
  authorization before it should be considered an isolation boundary.

## Verify Result

- PASS static: `go test -tags goolm ./...` in `go-appservice`.
- PASS static: `uv run pytest tests/bridge/test_nats_handler.py tests/agent/test_streaming_a2ui.py -q` in `python-backend`.
- PASS static: Python bridge subscribes to global and routed inbound subjects
  in `tests/bridge/test_nats_handler.py`.
- PASS static: `uv run ruff check bridge tests/bridge agent voice` in
  `python-backend`.

## Live Verify Result

Pending A4 E2E.

## Follow-Ups

- Run A4 unencrypted and encrypted live Matrix -> Go -> NATS -> Python -> NATS
  -> Go -> Matrix verification.
- Live-test enabled subject routing and keep it disabled for isolation claims
  until NATS authorization exists.
- Verify key backup, cross-signing, key deletion and restart behavior against a
  live homeserver.
