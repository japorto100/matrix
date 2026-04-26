---
title: Database Schema Governance Plan
status: planned
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
---

# Plan

1. Inventory existing Alembic migrations and schemas.
2. Decide registry format: Python `schema_registry.py`, generated Markdown, or
   both.
3. Add DB introspection helper for Postgres schemas/tables/columns/indexes.
4. Add tests that run after Alembic head and compare critical schema fields.
5. Add migration authoring checklist to SDD gates.
6. Apply the workflow first to Feature 017 KG tables.

Preferred default: Alembic authoritative, `docs/database/current-schema.md`
generated from DB introspection, and optional Python registry for code-facing
contracts.
