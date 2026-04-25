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

## Target State / Soll

The local stack can be bootstrapped predictably on the Linux Mint machine:
Compose profiles are documented, env files are generated/synced safely, secrets
are handled through SOPS/age, and Postgres defaults fit the 8GB host.

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

- Convert implementation notes into `closeout.md`.
- Keep only live environment drift as open work.
- Decide whether the env-layout finding becomes an ADR.
- Reconcile legacy Windows-specific commands with current Linux-first runtime.

## Verify

- [ ] Compose parse still passes.
- [ ] Shell syntax for scripts passes.
- [ ] Secrets bootstrap runbook is operator-verifiable.
- [ ] Postgres tuning assumptions still fit current hardware.

## Closeout Criteria

- Legacy implementation docs are summarized as done.
- Open operational checks are explicit live-verify tasks, not hidden in old execs.
