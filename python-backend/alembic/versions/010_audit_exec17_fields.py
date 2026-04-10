"""Add iteration column + full-text search index for exec-17 trace inspection.

The MCP Trace Tools (exec-17 Phase 4) need:
- iteration: which graph loop iteration produced this event
- Full-text search across input/output for trace_search() MCP tool
- thread_id + action composite for fast session trace retrieval

Revision ID: 010
Revises: 009
Create Date: 2026-04-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def upgrade() -> None:
    # iteration column — tracks which graph loop iteration
    op.add_column(
        "audit_events",
        sa.Column("iteration", sa.Integer, nullable=True),
        schema=SCHEMA,
    )

    # Composite index for trace_detail: get all events for a thread, ordered
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_audit_thread_timestamp "
        f"ON {SCHEMA}.audit_events (thread_id, timestamp)"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.ix_audit_thread_timestamp")
    op.drop_column("audit_events", "iteration", schema=SCHEMA)
