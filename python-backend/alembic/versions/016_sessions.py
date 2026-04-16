"""agent.sessions — central session table (exec-18 Phase 1).

Foundation for all exec-18 FKs (traces, evals, components, session_memories).
Agno SESSION_TABLE_SCHEMA adapted: +thread_id (legacy compat), +bank_id
(Hindsight bridge), +status, +started_at/completed_at.

Revision ID: 016_sessions
Revises: 015_skill_extensions
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "016_sessions"
down_revision = "015_skill_extensions"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.Text(), primary_key=True),
        sa.Column("session_type", sa.Text(), nullable=False),
        # agent_chat | matrix_mention | api | harness_eval
        sa.Column("agent_id", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("thread_id", sa.Text(), nullable=True),
        sa.Column("bank_id", sa.Text(), nullable=True),
        sa.Column("session_data", postgresql.JSONB(), nullable=True),
        sa.Column("agent_data", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("runs", postgresql.JSONB(), nullable=True),
        sa.Column("summary", postgresql.JSONB(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="active",
        ),
        sa.Column("started_at", sa.BigInteger(), nullable=False),
        sa.Column("completed_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sessions_thread_id", "sessions", ["thread_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_sessions_user_id", "sessions", ["user_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_sessions_bank_id", "sessions", ["bank_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_sessions_type_status",
        "sessions",
        ["session_type", "status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sessions_created_at", "sessions", ["created_at"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_created_at", "sessions", schema=SCHEMA)
    op.drop_index("ix_sessions_type_status", "sessions", schema=SCHEMA)
    op.drop_index("ix_sessions_bank_id", "sessions", schema=SCHEMA)
    op.drop_index("ix_sessions_user_id", "sessions", schema=SCHEMA)
    op.drop_index("ix_sessions_thread_id", "sessions", schema=SCHEMA)
    op.drop_table("sessions", schema=SCHEMA)
