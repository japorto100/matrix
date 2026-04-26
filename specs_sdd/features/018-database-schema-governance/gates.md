---
title: Database Schema Governance Gates
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
---

# Gates

- Alembic remains the authoritative migration path.
- No new table/column lands without an Alembic migration.
- Current schema view is updated or regenerated with every schema migration.
- DB introspection after `alembic upgrade head` matches the declared current
  schema for critical fields.
- Postgres extensions are created idempotently in migrations.
- Feature ownership is visible for every major table.
- Manual `init.sql` is not a runtime prerequisite.
