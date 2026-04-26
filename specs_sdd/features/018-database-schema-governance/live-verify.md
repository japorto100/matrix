---
title: Database Schema Governance Live Verify
status: pending
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
---

# Live Verify

- Start Matrix Postgres.
- Run `alembic upgrade head`.
- Generate schema inventory.
- Compare inventory against registry/current-schema.
- Add one sample migration in a branch and verify checklist catches missing
  registry/test updates.
