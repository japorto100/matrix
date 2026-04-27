from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

from scripts.schema_inventory import (
    ColumnInfo,
    ConstraintInfo,
    IndexInfo,
    SchemaInventory,
    format_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "alembic" / "versions"
CURRENT_SCHEMA = ROOT.parent / "docs" / "database" / "current-schema.md"


def _migration_assignments(path: Path) -> dict[str, str | tuple[str, ...] | None]:
    tree = ast.parse(path.read_text())
    assignments: dict[str, str | tuple[str, ...] | None] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        for target in targets:
            if (
                not isinstance(target, ast.Name)
                or target.id not in {"revision", "down_revision"}
                or value is None
            ):
                continue
            if isinstance(value, ast.Constant):
                assignments[target.id] = value.value
            elif isinstance(value, ast.Tuple):
                assignments[target.id] = tuple(
                    item.value for item in value.elts if isinstance(item, ast.Constant)
                )
    return assignments


def test_alembic_revision_graph_has_single_current_head() -> None:
    revisions: set[str] = set()
    referenced_down_revisions: set[str] = set()

    for path in VERSIONS.glob("*.py"):
        values = _migration_assignments(path)
        revision = values.get("revision")
        down_revision = values.get("down_revision")
        assert isinstance(revision, str), path
        assert revision not in revisions, f"duplicate Alembic revision {revision}"
        revisions.add(revision)
        if isinstance(down_revision, str):
            referenced_down_revisions.add(down_revision)
        elif isinstance(down_revision, tuple):
            referenced_down_revisions.update(down_revision)

    heads = revisions - referenced_down_revisions

    assert heads == {"032_user_agent_settings"}


def test_current_schema_doc_tracks_critical_feature_017_and_012_tables() -> None:
    source = CURRENT_SCHEMA.read_text()

    assert "python-backend/scripts/schema_inventory.py" in source
    assert "`agent.mempalace_drawers`" in source
    assert "`agent.kg_entities`" in source
    assert "`agent.kg_claims`" in source
    assert "`agent.kg_claim_evidence`" in source
    assert "`agent.kg_projection_outbox`" in source
    assert "`agent.user_agent_settings`" in source
    assert "`ingestion.source_artifacts`" in source
    assert "`btree_gist`" in source
    assert "`vector`" in source
    assert "`sys_period`" in source
    assert "Owner feature: `017`" in source
    assert "Owner feature: `021`" in source


def test_schema_inventory_markdown_includes_owners_indexes_and_constraints() -> None:
    inventory = SchemaInventory(
        alembic_revisions=("030_global_kg_bitemporal_claims",),
        extensions=("btree_gist", "vector"),
        columns=(
            ColumnInfo("agent", "kg_claims", "claim_id", "text", False, None, "NEVER"),
            ColumnInfo("agent", "kg_claims", "sys_period", "tstzrange", True, None, "ALWAYS"),
        ),
        indexes=(
            IndexInfo(
                "agent",
                "kg_claims",
                "ix_kg_claims_valid_period",
                "CREATE INDEX ix_kg_claims_valid_period ON agent.kg_claims USING gist (valid_period)",
            ),
        ),
        constraints=(
            ConstraintInfo(
                "agent",
                "kg_claims",
                "ex_kg_claims_current_conflict",
                "x",
                "EXCLUDE USING gist (conflict_key WITH =, valid_period WITH &&)",
            ),
        ),
    )

    markdown = format_markdown(
        inventory,
        generated_at=datetime(2026, 4, 27, 12, 0, tzinfo=UTC),
    )

    assert "Generated: `2026-04-27T12:00:00+00:00`" in markdown
    assert "Owner feature: `017`" in markdown
    assert "`ix_kg_claims_valid_period`" in markdown
    assert "`ex_kg_claims_current_conflict`" in markdown
