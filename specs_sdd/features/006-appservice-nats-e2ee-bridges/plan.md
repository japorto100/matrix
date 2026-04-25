---
title: Appservice, NATS, E2EE and Bridges Plan
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 006
migrated_from:
  - specs/execution/exec-05-nats-e2ee-pipeline.md
  - specs/execution/exec-05b-messaging-bridges.md
  - specs/execution/exec-05c-agent-isolation.md
adrs: []
---

# Plan

## Architecture

The Go appservice is the Matrix-facing crypto gateway. Python agents consume
and publish through NATS. Bridges and isolation extend this path but must not
blur the E2EE trust boundary.

## Critical Files

- `go-appservice/cmd/appservice/main.go`
- `go-appservice/internal/handler/**`
- `go-appservice/internal/natsbridge/**`
- `go-appservice/internal/crypto/**`
- `python-backend/bridge/**`
- `python-backend/agent/**`
- `docker-compose.yml`

## Migration Strategy

1. Convert exec-05 A/B phases into closeout.
2. Keep A4 E2E as primary live verify.
3. Split non-Matrix content ingestion from messaging bridges.
4. Keep agent isolation as a subfeature until implemented/live-verified.

## Risks

- Verifying NATS alone without proving Matrix encryption handoff.
- Mixing future bridge backlog with current E2EE gateway closure.

