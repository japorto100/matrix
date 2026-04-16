"""agent.components + component_configs + component_links (exec-18).

Versionierte Agent-Configs mit Pareto-Frontier Flag. Replaces filesystem
data/harness/candidates/ with DB persistence. Agno COMPONENT_TABLE_SCHEMA
adapted: +parent_version, +proposer_model, +pareto_frontier.

Revision ID: 018_components
Revises: 017_traces_spans
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "018_components"
down_revision = "017_traces_spans"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "components",
        sa.Column("component_id", sa.Text(), primary_key=True),
        sa.Column("component_type", sa.Text(), nullable=False),
        # agent | tool | memory_config | skill | prompt_template
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.Column("deleted_at", sa.BigInteger(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_components_type",
        "components",
        ["component_type"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_components_name", "components", ["name"], schema=SCHEMA
    )

    op.create_table(
        "component_configs",
        sa.Column("component_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column(
            "stage",
            sa.Text(),
            nullable=False,
            server_default="draft",
        ),
        # draft | published | archived
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("parent_version", sa.Integer(), nullable=True),
        sa.Column("proposer_model", sa.Text(), nullable=True),
        sa.Column(
            "pareto_frontier",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.Column("deleted_at", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("component_id", "version"),
        sa.ForeignKeyConstraint(
            ["component_id"],
            [f"{SCHEMA}.components.component_id"],
            name="fk_configs_component",
            ondelete="CASCADE",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_configs_stage",
        "component_configs",
        ["stage"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_configs_created_at",
        "component_configs",
        ["created_at"],
        schema=SCHEMA,
    )

    op.create_table(
        "component_links",
        sa.Column("parent_component_id", sa.Text(), nullable=False),
        sa.Column("parent_version", sa.Integer(), nullable=False),
        sa.Column("link_kind", sa.Text(), nullable=False),
        # uses_tool | uses_memory_bank | inherits_from | references_skill
        sa.Column("link_key", sa.Text(), nullable=False),
        sa.Column("child_component_id", sa.Text(), nullable=False),
        sa.Column("child_version", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint(
            "parent_component_id",
            "parent_version",
            "link_kind",
            "link_key",
        ),
        sa.ForeignKeyConstraint(
            ["parent_component_id", "parent_version"],
            [
                f"{SCHEMA}.component_configs.component_id",
                f"{SCHEMA}.component_configs.version",
            ],
            name="fk_links_parent_config",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["child_component_id"],
            [f"{SCHEMA}.components.component_id"],
            name="fk_links_child_component",
            ondelete="CASCADE",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_links_kind",
        "component_links",
        ["link_kind"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_links_kind", "component_links", schema=SCHEMA)
    op.drop_table("component_links", schema=SCHEMA)
    op.drop_index("ix_configs_created_at", "component_configs", schema=SCHEMA)
    op.drop_index("ix_configs_stage", "component_configs", schema=SCHEMA)
    op.drop_table("component_configs", schema=SCHEMA)
    op.drop_index("ix_components_name", "components", schema=SCHEMA)
    op.drop_index("ix_components_type", "components", schema=SCHEMA)
    op.drop_table("components", schema=SCHEMA)
