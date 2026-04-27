---
title: Database Schema Governance Plan
status: implementation_done
owner: filip
created: 2026-04-26
updated: 2026-04-27
feature_id: 018
---

# Plan

1. [done-static] Inventory existing Alembic migrations and schemas.
2. [done-static] Decide registry format: Python `schema_registry.py`, generated Markdown, or
   both.
3. [done-static] Add DB introspection helper for Postgres schemas/tables/columns/indexes.
4. [done-static] Add tests that run after Alembic head and compare critical schema fields.
5. [done-static] Add migration authoring checklist to SDD gates.
6. [done-static] Apply the workflow first to Feature 017 KG tables.
7. [done-live] Regenerate the inventory from a fresh local Postgres after
   `alembic upgrade head`.

Preferred default: Alembic authoritative, `docs/database/current-schema.md`
generated from DB introspection, and optional Python registry for code-facing
contracts.
