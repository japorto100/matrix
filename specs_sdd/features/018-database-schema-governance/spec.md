---
title: Database Schema Governance
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
migrated_from:
  - python-backend/alembic
  - _ref/agno/libs/agno/agno/db/postgres/schemas.py
  - _ref/agno/libs/agno/agno/db/migrations/manager.py
---

# Database Schema Governance

## Current State / Ist

Matrix already uses Alembic migrations for the Python/Postgres schema and the
agent can run `alembic upgrade head` during development startup. That is good
for DB evolution, but it is hard to answer a basic review question: which
tables and columns exist at the current head?

Agno-style schema dictionaries are easier to read, but Agno still has its own
migration manager. For Matrix, replacing Alembic would lose useful Postgres
migration semantics.

## Target State / Soll

Alembic remains authoritative for DB changes. A generated or maintained current
schema registry gives humans and agents a readable end-state view. Tests compare
the registry against a real database after `alembic upgrade head`, so registry
and migrations cannot drift silently.

Every new table or field must ship as:

- Alembic migration.
- schema registry/current-schema update.
- migration/introspection test.
- owner feature reference.

## Non-Goals

- Replace Alembic with a custom migration manager.
- Use schema registry as runtime migration source.
- Require manual SQL setup outside migrations.

## Closeout Criteria

- Current schema is visible from one stable file or generated doc.
- Alembic-head DB introspection matches that schema view.
- New migrations have a checklist/gate requiring registry and tests.
- Feature 017 KG schema uses this workflow.
