---
title: Database Schema Governance Research
status: draft
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
---

# Research

Agno exposes readable table schema dictionaries in
`_ref/agno/libs/agno/agno/db/postgres/schemas.py`, which is useful for humans
and agents. It also keeps a migration manager in
`_ref/agno/libs/agno/agno/db/migrations/manager.py`, so the model is not
"schema.py instead of migrations"; it is readable schema plus migration state.

Matrix should keep Alembic because the project uses Postgres-specific features:
schemas, range types, pgvector, partial indexes, generated columns, extension
management and data migrations. The missing part is visibility of the final
head schema.

Recommended pattern:

- Alembic is truth for changes.
- introspection generates current schema docs.
- optional registry captures intended contract and owner feature.
- tests catch drift.
