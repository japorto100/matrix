"""agent.evals — persisted harness and benchmark evaluation runs.

Feature 014/016/022/023 use this table as the durable handoff between
one-off eval execution, Meta-Harness proposer loops and Control/analysis
surfaces. `meta_harness.evals_store` already writes this shape; the migration
keeps Alembic authoritative instead of relying on ad hoc table creation.

Revision ID: 033_agent_evals
Revises: 032_user_agent_settings
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "033_agent_evals"
down_revision = "032_user_agent_settings"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")
    op.create_table(
        "evals",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("eval_type", sa.Text(), nullable=False),
        sa.Column("eval_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("eval_input", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("agent_id", sa.Text(), nullable=True),
        sa.Column("model_id", sa.Text(), nullable=True),
        sa.Column("model_provider", sa.Text(), nullable=True),
        sa.Column("component_id", sa.Text(), nullable=True),
        sa.Column("component_version", sa.Integer(), nullable=True),
        sa.Column("evaluated_component_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_evals_type_created",
        "evals",
        ["eval_type", "created_at"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_evals_component",
        "evals",
        ["evaluated_component_name", "component_id", "component_version"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_evals_agent_model",
        "evals",
        ["agent_id", "model_provider", "model_id"],
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_evals_agent_model", "evals", schema=SCHEMA, if_exists=True)
    op.drop_index("ix_evals_component", "evals", schema=SCHEMA, if_exists=True)
    op.drop_index("ix_evals_type_created", "evals", schema=SCHEMA, if_exists=True)
    op.drop_table("evals", schema=SCHEMA, if_exists=True)
