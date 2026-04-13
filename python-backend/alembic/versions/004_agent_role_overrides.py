"""Create agent.agent_role_overrides for D1 DB Overlay pattern.

Trading roles have hardcoded defaults in agent/roles.py. This table holds
user-specific overrides that are merged on load. PATCH endpoints in
agent/control/agents.py UPSERT here.

Revision ID: 004
Revises: 003
Create Date: 2026-04-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "agent_role_overrides",
        sa.Column("role_id", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text, nullable=False, server_default="local"),
        sa.Column("field", sa.Text, nullable=False),
        sa.Column("value", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("updated_by", sa.Text, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("role_id", "user_id", "field"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_role_overrides_role_user",
        "agent_role_overrides",
        ["role_id", "user_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_role_overrides_role_user", "agent_role_overrides", schema=SCHEMA)
    op.drop_table("agent_role_overrides", schema=SCHEMA)
