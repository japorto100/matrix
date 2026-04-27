"""agent.user_agent_settings — per-user agent prompt/memory/tool policy.

The runtime already treats this table as optional configuration. Creating it
removes noisy runtime query failures and gives Control UI a durable target for
future per-agent settings.

Revision ID: 032_user_agent_settings
Revises: 031_ingestion_source_artifacts
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "032_user_agent_settings"
down_revision = "031_ingestion_source_artifacts"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")
    op.create_table(
        "user_agent_settings",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.Text(), nullable=False, server_default="default"),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "agent_id"),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_user_agent_settings_user",
        "user_agent_settings",
        ["user_id"],
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_agent_settings_user",
        "user_agent_settings",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("user_agent_settings", schema=SCHEMA, if_exists=True)
