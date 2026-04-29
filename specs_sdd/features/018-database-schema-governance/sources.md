---
title: Database Schema Governance Sources
status: draft
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
---

# Sources

| Source | Use |
|---|---|
| `python-backend/alembic/**` | Existing authoritative migrations. |
| `python-backend/agent/startup_migrations.py` | Dev startup migration behavior. |
| `_ref/agno/libs/agno/agno/db/postgres/schemas.py` | Readable schema dictionary pattern. |
| `_ref/agno/libs/agno/agno/db/migrations/manager.py` | Agno migration-manager comparison. |
| `specs_sdd/features/017-knowledge-graph-bitemporal-claims` | First consumer for bitemporal KG schema workflow. |
