---
title: Devstack Bootstrap Env Persistence Gates
status: draft
owner: filip
created: 2026-04-25
updated: 2026-04-25
feature_id: 002
---

# Gates

- [ ] Compose file parses.
- [ ] `scripts/dev-stack.sh` shell syntax passes.
- [ ] Env examples exist for frontend, Go appservice and Python backend.
- [ ] Alembic migrations can run against local Postgres.
- [ ] Secrets bootstrap runbook is operator-verifiable without committing clear
  secrets.
- [ ] Postgres settings are reviewed against 8GB RAM machine.
- [ ] HDD/SSD placement follows local policy.
