---
title: Devstack Bootstrap, Env and Persistence Ops Tasks
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
---

# Tasks

- [x] T001 Summarize devstack implementation state into `closeout.md`.
- [x] T002 Extract env layout rationale into `research.md` or ADR candidate.
- [x] T003 [P] Verify shell syntax for scripts -> `scripts/*.sh`.
- [x] T004 [P] Verify compose parse -> `docker-compose.yml`.
- [x] T005 [P] Verify env examples are present for frontend, Go and Python.
- [x] T006 Run operator bootstrap smoke or document why local secrets prevent it.
- [x] T007 Mark archived `exec-19` stages as split across owning features.
- [x] T008 [done-live] Keep Matrix infrastructure isolated from other projects:
  `matrix-postgres` uses `matrix_postgres-data` on `5433`; `matrix-nats`
  uses `matrix_nats-data` on host `14222/18222` so Tradeview's NATS on
  `4222/8222` is not reused accidentally.
- [x] T009 [done-static] After port/service changes, update local env files and
  `scripts/bootstrap-env.py` defaults in the same pass.

## Verify Gates

- [x] `bash -n scripts/*.sh`
- [x] Compose YAML parses.
- Alembic head is reachable when Postgres is running. Deferred to live/operator verify.
- [x] Matrix-NATS host port is owned by `matrix-nats`, not a foreign project
  container.
- [x] Env examples match documented service roles.
