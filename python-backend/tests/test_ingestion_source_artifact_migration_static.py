from __future__ import annotations

import importlib.util
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "031_ingestion_source_artifacts.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("source_artifact_migration", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ingestion_source_artifact_migration_revision_chain() -> None:
    module = _load_migration()

    assert module.revision == "031_ingestion_source_artifacts"
    assert module.down_revision == "030_global_kg_bitemporal_claims"


def test_ingestion_source_artifact_migration_contains_provenance_contract() -> None:
    source = MIGRATION.read_text()

    assert "source_artifacts" in source
    assert "source_uri" in source
    assert "content_hash" in source
    assert "parser_name" in source
    assert "chunker_name" in source
    assert "embedding_provider" in source
    assert "ux_source_artifacts_uri_hash" in source
