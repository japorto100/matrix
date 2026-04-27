---
title: Devstack Bootstrap, Env and Persistence Ops
status: implementation_done
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 002
migrated_from:
  - specs/05-devstack.md
  - specs/execution/exec-linux-setup-users-2026-04-17.md
  - specs/execution/exec-secrets-bootstrap-2026-04-17.md
  - specs/execution/exec-postgres-tuning-2026-04-17.md
  - specs/execution/archive/exec-19-devstack-consolidation.md
  - docs/superpowers/findings/2026-04-24-env-layout-decision.md
adrs: []
---

# Devstack Bootstrap, Env and Persistence Ops

## Current State / Ist

Devstack, env bootstrap, user setup, secrets bootstrap and Postgres tuning are
mostly implemented. `exec-19` is archived and split across this feature, the
frontend merger, LLM routing and research backlog. The active machine target is
Linux Mint with SSD/HDD split; hot build/runtime artifacts stay on SSD while
cold package/model caches can live on HDD.

Static bootstrap gates passed on 2026-04-25: shell syntax for `scripts/*.sh`,
compose parse for `docker-compose.yml`, and env-example presence for the root,
frontend, Go appservice and Python backend scopes.

## Target State / Soll

The local stack can be bootstrapped predictably on the Linux Mint machine:
Compose profiles are documented, env files are generated/synced safely, secrets
are handled through SOPS/age, and Postgres defaults fit the 8GB host.
Matrix-owned infrastructure must not silently attach to another project's
running containers. Local Matrix NATS therefore uses host `14222/18222` with
its own `matrix_nats-data` volume; Postgres uses `5433` and
`matrix_postgres-data`.

## Subfeatures

- Linux dev-stack scripts
- Root and service env layout
- SOPS/age secret bootstrap
- User setup scripts
- Postgres tuning, pooler, exporter and backup
- Compose profile documentation
- Linux `dev-stack.sh` / historical Windows `dev-stack*.ps1` split
- Storage/cache placement policy

## Gap

- Operator/live bootstrap smoke remains open because it requires a running local
  stack and secrets.
- Alembic reachability remains a live/operator gate tied to a running Postgres.
- Devstack status must be interpreted as Matrix-owned service health, not just
  "some process listens on the port"; this was tightened after a Tradeview
  NATS instance occupied `4222`.
- Env-layout rationale is documented in `research.md`; promote to ADR only if
  automatic env generation/validation becomes binding.
- Legacy Windows-specific commands are historical/porting material, not the
  Linux-first runtime path.

## Verify

- [x] Compose parse still passes.
- [x] Shell syntax for scripts passes.
- [x] Secrets bootstrap runbook is operator-verifiable.
- [x] Postgres tuning assumptions still fit current hardware.

## Closeout Criteria

- Legacy implementation docs are summarized as done.
- Open operational checks are explicit live-verify tasks, not hidden in old execs.
