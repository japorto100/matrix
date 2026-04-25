---
title: Devstack Bootstrap, Env and Persistence Ops Plan
status: draft
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

# Plan

## Architecture

This feature owns local stack bootstrap: shell scripts, compose profiles, env
layout, secrets, Postgres tuning and operator runbooks.

## Critical Files

- `scripts/dev-stack.sh`
- `scripts/setup-users.sh`
- `scripts/register-appservice.sh`
- `docker-compose.yml`
- `.env.example`
- `go-appservice/.env.example`
- `python-backend/.env.example`
- `frontend_merger/env.example.merger`

## Migration Strategy

1. Condense completed execs into closeout.
2. Keep env-layout decision as research unless it becomes binding ADR.
3. Convert operator checks into live verify.

## Risks

- Env duplication being treated as accidental instead of role-based.
- Postgres tuning drifting from the actual 8GB host constraints.

