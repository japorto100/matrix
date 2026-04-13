"""Create agent.a2a_delegations persistent log.

Currently A2AClient (agent/a2a/client.py) produces ephemeral A2ATask objects.
This table persists every delegation so the control UI /a2a tab can show
history + status + result preview.

Revision ID: 006
Revises: 005
Create Date: 2026-04-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "a2a_delegations",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("from_role", sa.Text, nullable=False),
        sa.Column("to_role", sa.Text, nullable=False),
        sa.Column("task", sa.Text, nullable=False),
        sa.Column(
            "status", sa.Text, nullable=False
        ),  # pending|running|completed|failed
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("thread_id", sa.Text, nullable=True),
        sa.Column("user_id", sa.Text, nullable=False, server_default="local"),
        schema=SCHEMA,
    )

    op.create_index("ix_a2a_status", "a2a_delegations", ["status"], schema=SCHEMA)
    op.create_index("ix_a2a_thread", "a2a_delegations", ["thread_id"], schema=SCHEMA)
    op.create_index(
        "ix_a2a_started_desc",
        "a2a_delegations",
        [sa.text("started_at DESC")],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_a2a_started_desc", "a2a_delegations", schema=SCHEMA)
    op.drop_index("ix_a2a_thread", "a2a_delegations", schema=SCHEMA)
    op.drop_index("ix_a2a_status", "a2a_delegations", schema=SCHEMA)
    op.drop_table("a2a_delegations", schema=SCHEMA)
