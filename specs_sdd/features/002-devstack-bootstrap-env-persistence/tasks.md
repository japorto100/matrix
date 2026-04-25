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

- [ ] T001 Summarize devstack implementation state into `closeout.md`.
- [ ] T002 Extract env layout rationale into `research.md` or ADR candidate.
- [ ] T003 [P] Verify shell syntax for scripts -> `scripts/*.sh`.
- [ ] T004 [P] Verify compose parse -> `docker-compose.yml`.
- [ ] T005 [P] Verify env examples are present for frontend, Go and Python.
- [ ] T006 Run operator bootstrap smoke or document why local secrets prevent it.
- [ ] T007 Mark archived `exec-19` stages as split across owning features.

## Verify Gates

- [ ] `bash -n scripts/*.sh`
- [ ] Compose YAML parses.
- [ ] Alembic head is reachable when Postgres is running.
- [ ] Env examples match documented service roles.

