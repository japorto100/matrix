"""agent.sync_failures — ops-visibility log for post-turn memory-sync errors.

exec-hermes Phase-B P1 wires ``MemoryManager.sync_turn()`` as a
fire-and-forget background task (``asyncio.create_task``) so the user's
turn-latency is not affected by memory-persistence. If the background
task fails (Hindsight/MemPalace down, DB glitch, timeout), we need an
ops-visible signal rather than a silent log-line nobody reads.

The ``_safe_sync_turn`` wrapper (in ``runner.py``) INSERTs into this
table whenever it catches an exception. Rows are short-lived (transient
ops signal) — a scheduled prune job strips rows older than 30 days
(Phase-C cleanup task, or pg_partman).

ADR note:
- Phase-B acceptance: fire-and-forget + visibility-table is a pragmatic
  trade-off. Turn-latency stays low, ops can see sync-failure rates.
- Phase-C migration path: switch to at-least-once delivery via NATS-
  JetStream consumer if measured memory-loss impact justifies the
  complexity. The table stays as tier-2 ops-visibility either way.

Revision ID: 022_agent_sync_failures
Revises: 021_agent_metrics
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "022_agent_sync_failures"
down_revision = "021_agent_metrics"
branch_labels = None
depends_on = None

# Migration-numbering: Phase-B plan originally reserved
#   022 redaction_patterns (P3), 023 sync_failures (P1), 024 sessions.title (P6)
# but assumed all three land atomically. P1 is the first Phase-B phase to
# merge, so sync_failures takes 022 here. P3's redaction_patterns will be 023,
# P6's sessions.title will be 024. Creation order == revision order keeps
# Alembic's linear chain valid.

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "sync_failures",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        # turn_id is nullable because sync_turn can fire before a turn_id
        # has been assigned (e.g. background prefetch-retry on an
        # unidentified session).
        sa.Column("turn_id", sa.Text(), nullable=True),
        sa.Column("thread_id", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sync_failures_created_at",
        "sync_failures",
        ["created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sync_failures_user_created",
        "sync_failures",
        ["user_id", "created_at"],
        schema=SCHEMA,
    )
    # Retention-note for ops: prune rows older than 30 days. Implement
    # via Phase-C scheduled cleanup (exec-scheduler) or pg_partman
    # partition-drop if volume justifies partitioning later.


def downgrade() -> None:
    op.drop_index(
        "ix_sync_failures_user_created", "sync_failures", schema=SCHEMA
    )
    op.drop_index(
        "ix_sync_failures_created_at", "sync_failures", schema=SCHEMA
    )
    op.drop_table("sync_failures", schema=SCHEMA)
