from __future__ import annotations

import importlib.util
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "030_global_kg_bitemporal_claims.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("kg_claim_migration", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_kg_claim_migration_revision_chain() -> None:
    module = _load_migration()

    assert module.revision == "030_global_kg_bitemporal_claims"
    assert module.down_revision == "029_mempalace_pgvector_drawers"


def test_kg_claim_migration_contains_bitemporal_and_projection_contracts() -> None:
    source = MIGRATION.read_text()

    assert "kg_entities" in source
    assert "kg_claims" in source
    assert "valid_period" in source
    assert "sys_period" in source
    assert "ex_kg_claims_current_conflict" in source
    assert "kg_claim_evidence" in source
    assert "kg_projection_outbox" in source
    assert "projection_target IN ('nornicdb')" in source
    assert "CREATE EXTENSION IF NOT EXISTS vector" in source
