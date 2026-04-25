---
title: Devstack Bootstrap Env Persistence Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 002
---

# Gates

- [x] Compose file parses.
- [x] `scripts/dev-stack.sh` shell syntax passes.
- [x] Env examples exist for frontend, Go appservice and Python backend.
- [ ] Alembic migrations can run against local Postgres. Deferred to
  `live-verify.md` because it requires a running local Postgres profile.
- [x] Secrets bootstrap runbook is operator-verifiable without committing clear
  secrets.
- [x] Postgres settings are reviewed against 8GB RAM machine.
- [x] HDD/SSD placement follows local policy.

## Static Evidence

Checked on 2026-04-25:

- `bash -n scripts/*.sh`
- `podman compose -f docker-compose.yml config`
- env examples present at `.env.example`, `frontend_merger/.env.example`,
  `go-appservice/.env.example`, `python-backend/.env.example` and
  `python-backend/ingestion/.env.example`
