---
title: Database Schema Governance Tasks
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-27
feature_id: 018
---

# Tasks

## Inventory

- T001 [done-static] List current Alembic heads and branch state.
- T002 [partial-static] Generate current DB table/column/index inventory from a fresh
  `alembic upgrade head`.
- T003 [done-static] Identify undocumented schemas/tables.

## Registry

- T010 [done-static] Decide registry output: generated Markdown plus reviewed
  current-schema Markdown; no runtime schema.py replacement.
- T011 [done-static] Define table metadata fields: schema, table, owner feature, columns,
  indexes, constraints, extensions and lifecycle notes.
- T012 [done-static] Add owner feature references for existing major tables.
- T013 [done-static] Add docs path: `docs/database/current-schema.md`.

## Tests And Gates

- T020 [done-static] Add introspection/static test for critical tables and columns.
- T021 [done-static] Add test that fails on Alembic head mismatch.
- T022 [done-static] Add migration checklist: migration + registry/doc + test + owner feature.
- T023 [done-static] Add extension checks for `vector`, `btree_gist` and other Postgres
  features when used.
- T024 [done-static] Add dev command for schema inventory regeneration.

## Feature 017 Integration

- T030 [done-static] Use this workflow for KG bitemporal claim tables.
- T031 [done-static] Test generated columns, range types, indexes and pgvector dimensions.
- T032 [done-static] Document downgrade/data-migration stance for KG schema changes.

## Live Gate

- T040 [done-live] Run `alembic upgrade head` against a freshly booted local Postgres and
  regenerate `docs/database/current-schema.md` from live introspection.
