"""agent.prompt_cache_thread_summaries — durable cache telemetry rollups.

Revision ID: 034_prompt_cache_aggregates
Revises: 033_agent_evals
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "034_prompt_cache_aggregates"
down_revision = "033_agent_evals"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")
    op.create_table(
        "prompt_cache_thread_summaries",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cache_impact_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "cache_invalidation_count",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("cache_break_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cache_read_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cache_write_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("prompt_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "unknown_cache_fields",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "providers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "models",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "thread_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "thread_id"),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prompt_cache_user_last_seen "
        "ON agent.prompt_cache_thread_summaries (user_id, last_seen DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_prompt_cache_user_read_tokens "
        "ON agent.prompt_cache_thread_summaries (user_id, cache_read_tokens DESC)"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prompt_cache_user_read_tokens",
        "prompt_cache_thread_summaries",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ix_prompt_cache_user_last_seen",
        "prompt_cache_thread_summaries",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("prompt_cache_thread_summaries", schema=SCHEMA, if_exists=True)
