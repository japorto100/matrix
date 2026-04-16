"""agent.traces + agent.spans — persistent OTel storage (exec-18).

Parallel to OpenObserve (transient): spans flow to BOTH targets via
PostgresSpanProcessor. Enables SQL-joins: sessions JOIN traces JOIN spans
for harness analysis. Meta-Harness ablation: +15pp from trace access.

Revision ID: 017_traces_spans
Revises: 016_sessions
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "017_traces_spans"
down_revision = "016_sessions"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "traces",
        sa.Column("trace_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        # ok | error | timeout
        sa.Column("start_time", sa.Text(), nullable=False),
        sa.Column("end_time", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("agent_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            [f"{SCHEMA}.sessions.session_id"],
            name="fk_traces_session",
            ondelete="CASCADE",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_traces_status", "traces", ["status"], schema=SCHEMA)
    op.create_index(
        "ix_traces_session_id", "traces", ["session_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_traces_user_id", "traces", ["user_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_traces_created_at", "traces", ["created_at"], schema=SCHEMA
    )

    op.create_table(
        "spans",
        sa.Column("span_id", sa.Text(), primary_key=True),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("parent_span_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("span_kind", sa.Text(), nullable=False),
        # agent.session | agent.turn | agent.tool_call | agent.memory
        sa.Column("status_code", sa.Text(), nullable=False),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("start_time", sa.Text(), nullable=False),
        sa.Column("end_time", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("attributes", postgresql.JSONB(), nullable=True),
        sa.Column("events", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["trace_id"],
            [f"{SCHEMA}.traces.trace_id"],
            name="fk_spans_trace",
            ondelete="CASCADE",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_spans_trace_id", "spans", ["trace_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_spans_trace_parent",
        "spans",
        ["trace_id", "parent_span_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_spans_created_at", "spans", ["created_at"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_index("ix_spans_created_at", "spans", schema=SCHEMA)
    op.drop_index("ix_spans_trace_parent", "spans", schema=SCHEMA)
    op.drop_index("ix_spans_trace_id", "spans", schema=SCHEMA)
    op.drop_table("spans", schema=SCHEMA)
    op.drop_index("ix_traces_created_at", "traces", schema=SCHEMA)
    op.drop_index("ix_traces_user_id", "traces", schema=SCHEMA)
    op.drop_index("ix_traces_session_id", "traces", schema=SCHEMA)
    op.drop_index("ix_traces_status", "traces", schema=SCHEMA)
    op.drop_table("traces", schema=SCHEMA)
