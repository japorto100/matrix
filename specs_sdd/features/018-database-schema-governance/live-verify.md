---
title: Database Schema Governance Live Verify
status: pending
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
---

# Live Verify

- Start Matrix Postgres.
- Run `alembic upgrade head`.
- Generate schema inventory.
- Compare inventory against registry/current-schema.

## Static Evidence

- Added `python-backend/scripts/schema_inventory.py` for live Postgres
  introspection over schemas, columns, indexes, constraints, extensions and
  Alembic revisions.
- Added `docs/database/current-schema.md` as reviewed registry/checklist.
- Added `python-backend/tests/test_schema_governance.py` for single-head drift,
  required KG/MemPalace contracts and registry coverage.

## Live Command

```bash
cd python-backend
uv run alembic upgrade head
uv run python scripts/schema_inventory.py --output ../docs/database/current-schema.md
uv run pytest tests/test_schema_governance.py
```

## Live Evidence 2026-04-27

- Started local `postgres` container on `localhost:5433`.
- Ran Alembic with the local `.env` Postgres credentials; current Matrix
  revision is `030_global_kg_bitemporal_claims (head)`.
- Regenerated `docs/database/current-schema.md` from live Postgres
  introspection. The inventory now reports Matrix `agent` revision plus the
  existing Hindsight/public revision rows separately.
- Verification passed:
  `python-backend/.venv/bin/python -m pytest tests/test_schema_governance.py tests/test_kg_claim_migration_static.py`.
- Add one sample migration in a branch and verify checklist catches missing
  registry/test updates.
