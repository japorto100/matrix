---
title: Database Schema Governance Tasks
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-30
feature_id: 018
---

# Tasks

## Inventory

- T001 [done-static] List current Alembic heads and branch state.
- T002 [done-live] Generate current DB table/column/index inventory from a fresh
  `alembic upgrade head`.
  - 2026-04-27: verified against `matrix-postgres` on `localhost:5433`;
    `alembic current` reports `032_user_agent_settings (head)` and
    `tests/test_schema_governance.py` passes.
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
- T025 [done-live] Ensure the Matrix dev runner uses a dedicated
  `matrix-postgres` container and `matrix_postgres-data` volume, not another
  project's Postgres container/volume.
- T026 [done-live] Move the memory-eval compose Postgres host port away from
  Matrix's `5433` to prevent runner collisions.
- T027 [done-live] Add missing runtime-owned `agent.user_agent_settings`
  migration and regenerate schema inventory after `alembic upgrade head`.
- T028 [done-live] Verify cache/persistence helpers do not reuse another
  project's Redis/Valkey port: Matrix Valkey is `matrix-valkey` on `16379`,
  with generated Python Redis defaults updated accordingly.

## Feature 017 Integration

- T030 [done-static] Use this workflow for KG bitemporal claim tables.
- T031 [done-static] Test generated columns, range types, indexes and pgvector dimensions.
- T032 [done-static] Document downgrade/data-migration stance for KG schema changes.

## Live Gate

- T040 [done-live] Run `alembic upgrade head` against a freshly booted local Postgres and
  regenerate `docs/database/current-schema.md` from live introspection.
- T041 [done-live] Verify local Matrix Postgres exposes pgvector on `:5433`.
  - 2026-04-27: `matrix-postgres` runs `pgvector/pgvector:pg17` on
    `matrix_postgres-data`; extensions verified: `vector 0.8.2`,
    `btree_gist`, `pg_trgm`, `pg_stat_statements`.
- T042 [done-live] Verify Alembic head includes
  `032_user_agent_settings` and `agent.user_agent_settings` exists in live
  Postgres after upgrade.
- T043 [done-live] Verify Alembic head includes `033_agent_evals` and
  `agent.evals` exists in live Postgres after upgrade.
  - 2026-04-27: `alembic current` reports `033_agent_evals (head)`;
    regenerated `docs/database/current-schema.md` includes `agent.evals`.
- T044 Add schema governance for Feature 024 MCP descriptor snapshots if they
  become persistent.
- T045 [done-static] Add schema governance for Feature 025 semantic
  terms/metrics.
  - 2026-04-30: current semantic catalog remains code/static artifact owned by
    Feature 025, so no Alembic migration is required. If semantic terms/metrics
    become persistent, they must enter this workflow before merge.
- T046 Add schema governance for Feature 027 report manifests and Feature 028
  visual evidence if stored in Postgres.
- T047 Add schema governance for Feature 029 ops read models if materialized.
