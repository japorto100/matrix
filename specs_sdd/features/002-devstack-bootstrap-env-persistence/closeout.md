---
title: Devstack Bootstrap, Env and Persistence Ops Closeout
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-27
feature_id: 002
---

# Closeout

## Built

- Linux-first devstack orchestration exists in `scripts/dev-stack.sh` with
  presets for matrix core/chat/full/mobile/mock, agent dev, memory dev and
  sandbox dev.
- Bootstrap runbook exists in `scripts/devstack.md`, including first-start
  order, appservice-registration workaround, DB wipe scenarios, ports and
  config source of truth.
- Dev user setup exists in `scripts/setup-users.sh`.
- Tuwunel appservice registration helper exists in
  `scripts/register-appservice.sh`.
- Root, frontend, Go appservice and Python backend env examples exist.
- Matrix-local NATS, Postgres and Valkey are isolated by container name,
  host port and named volume: `matrix-nats` on `14222/18222`,
  `matrix-postgres` on `5433`, and `matrix-valkey` on `16379`.
- `scripts/dev-stack.sh --status` checks expected Matrix container ownership
  for compose-owned services, avoiding false-positive health from another
  project's open port.
- `exec-19` is no longer a single active execution plan. Its contents are split
  across Feature 002, Feature 003, Feature 011 and research backlog.

## Not Built

- No automatic full secret generation/rotation pipeline is closed here.
- No always-on env validator is implemented.
- Full operator bootstrap from a clean machine still needs an intentional
  end-to-end run.

## Deviations From Plan

- Windows-oriented legacy commands remain as provenance/porting context. The
  active runtime path is Linux-first.
- Env-layout decision is documented as feature research rather than accepted as
  an ADR.

## Verify Result

- PASS: `bash -n scripts/*.sh`
- PASS: `podman compose -f docker-compose.yml config`
- PASS: required env examples are present for root compose, frontend, Go
  appservice and Python backend.
- PASS: `matrix-valkey` runs on `:16379` and responds to `valkey-cli ping`;
  foreign Valkey on `:6379` is no longer reported as Matrix cache.
- PASS: `matrix-postgres` exposes pgvector after container restart and
  `dev-stack --status` reports it only when the Matrix container owns `:5433`.

## Live Verify Result

Partially executed on 2026-04-27. Matrix NATS/Postgres/Valkey ownership is
live-proven. Full user-facing Matrix/chat bootstrap remains in `live-verify.md`.

## Follow-Ups

- Promote env layout to an ADR only if future tooling depends on it.
- Run operator bootstrap after local secrets and service state are intentionally
  prepared.
