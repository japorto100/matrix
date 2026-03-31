"""Create audit_events table.

Revision ID: 001
Revises: None
Create Date: 2026-03-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text),
        sa.Column("thread_id", sa.Text),
        sa.Column("agent_class", sa.Text),
        sa.Column("agent_role", sa.Text),
        sa.Column("tool_name", sa.Text),
        sa.Column("input", sa.JSON),
        sa.Column("output", sa.JSON),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("success", sa.Boolean, default=True),
        sa.Column("error", sa.Text),
        sa.Column("metadata", sa.JSON),
        schema=SCHEMA,
    )
    op.create_index("ix_audit_user_id", "audit_events", ["user_id"], schema=SCHEMA)
    op.create_index("ix_audit_thread_id", "audit_events", ["thread_id"], schema=SCHEMA)
    op.create_index("ix_audit_action", "audit_events", ["action"], schema=SCHEMA)
    op.create_index("ix_audit_timestamp", "audit_events", ["timestamp"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("audit_events", schema=SCHEMA)
