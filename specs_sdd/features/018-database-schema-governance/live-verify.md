---
title: Database Schema Governance Live Verify
status: passed-backend-live
owner: filip
created: 2026-04-26
updated: 2026-04-26
feature_id: 018
---

# Live Verify

## 2026-04-29 Feature 024-029 Schema Follow-Up

- Regenerate schema docs after adding any Feature 024-029 persistent tables.
- Verify schema inventory lists semantic, visual/report and ops tables if
  implemented.

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

- Started local `matrix-postgres` container on `localhost:5433`.
- Ran Alembic with the local `.env` Postgres credentials; current Matrix
  revision is `032_user_agent_settings (head)`.
- Regenerated `docs/database/current-schema.md` from live Postgres
  introspection. The inventory now reports Matrix `agent` revision plus the
  existing Hindsight/public revision rows separately.
- Verification passed:
  `uv run pytest tests/test_schema_governance.py tests/agent/security/test_agent_settings.py`.
- 2026-04-27 recheck passed:
  `HINDSIGHT_DB_URL=postgresql://postgres:...@localhost:5433/hindsight_dev uv run alembic current`
  returned `032_user_agent_settings (head)` and
  `uv run pytest tests/test_schema_governance.py -q` returned `3 passed`.
- 2026-04-27 Feature 014 follow-up applied `033_agent_evals`; `alembic current`
  now returns `033_agent_evals (head)`, `docs/database/current-schema.md`
  includes `agent.evals`, and `tests/test_schema_governance.py -q` still
  returns `3 passed`.
- Runtime log issue investigated: Postgres itself did not crash; logs showed a
  clean smart shutdown and missing `agent.user_agent_settings` query errors.
  Revision `032_user_agent_settings` creates that table and live verification
  confirmed `to_regclass('agent.user_agent_settings')`.

## Remaining Non-Blocking Governance Drill

- Add one sample migration in a future branch and verify checklist catches
  missing registry/test updates.
