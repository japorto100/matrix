---
title: Database Schema Governance Gates
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-30
feature_id: 018
---

# Gates

## 2026-04-29 Feature 024-029 Schema Follow-Up

- Persistent MCP descriptor snapshots from Feature 024 require Alembic
  governance.
- Semantic term/metric tables from Feature 025 require generated schema docs.
- Report manifests, visual evidence and ops read models require migration
  ownership before production persistence.
- 2026-04-30: current Feature 025 semantic catalog/correction contract is
  static/code-backed, so no schema migration is required for
  `knowledge-contract`; persistence would reopen this gate.

- Alembic remains the authoritative migration path.
- No new table/column lands without an Alembic migration.
- Current schema view is updated or regenerated with every schema migration.
- DB introspection after `alembic upgrade head` matches the declared current
  schema for critical fields.
- Postgres extensions are created idempotently in migrations.
- Feature ownership is visible for every major table.
- Manual `init.sql` is not a runtime prerequisite.
