---
title: Alembic Current-Schema Governance
status: accepted
owner: filip
created: 2026-04-27
updated: 2026-04-27
feature_id: 018
---

# ADR 0007: Alembic Current-Schema Governance

## Decision

Matrix keeps Alembic as the authoritative migration system. We add a generated
or reviewed current-schema registry at `docs/database/current-schema.md` plus a
Postgres introspection helper at `python-backend/scripts/schema_inventory.py`.

## Rationale

Agno-style schema dictionaries are easier to read, but they are not a full
replacement for Alembic when using Postgres-specific features such as schemas,
range types, generated columns, exclusion constraints, partial indexes and
pgvector. The missing capability in Matrix is not migration execution; it is a
stable human/agent-readable view of the schema after `alembic upgrade head`.

## Consequences

- Every new table or critical field must update the current-schema registry or
  regenerated inventory.
- Critical migrations need tests for Alembic head drift and important columns,
  indexes, constraints or extensions.
- Feature 017 KG and Feature 012 Memory-Fusion schemas are the first governed
  contracts.
- The registry is documentation and review surface only; runtime code must not
  treat it as the migration source.
