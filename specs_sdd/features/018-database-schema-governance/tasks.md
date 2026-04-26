---
title: Database Schema Governance Tasks
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
---

# Tasks

## Inventory

- T001 List current Alembic heads and branch state.
- T002 Generate current DB table/column/index inventory from a fresh
  `alembic upgrade head`.
- T003 Identify undocumented schemas/tables.

## Registry

- T010 Decide registry output: generated Markdown, Python registry, or both.
- T011 Define table metadata fields: schema, table, owner feature, columns,
  indexes, constraints, extensions and lifecycle notes.
- T012 Add owner feature references for existing major tables.
- T013 Add docs path, likely `docs/database/current-schema.md`.

## Tests And Gates

- T020 Add introspection test for critical tables and columns.
- T021 Add test or script that fails on Alembic head mismatch.
- T022 Add migration checklist: migration + registry/doc + test + owner feature.
- T023 Add extension checks for `vector`, `btree_gist` and other Postgres
  features when used.
- T024 Add CI/dev command for schema inventory regeneration.

## Feature 017 Integration

- T030 Use this workflow for KG bitemporal claim tables.
- T031 Test generated columns, range types, indexes and pgvector dimensions.
- T032 Document downgrade/data-migration stance for KG schema changes.
