"""agent.ab_experiments — generic A/B experiment ledger (Phase-C P1).

Records every dispatched turn with the signals needed to compare runner
variants (SimpleLoop vs LangGraph for the first experiment) and any
future A/B splits we want to run. Designed as infrastructure that earns
its keep even without SimpleLoop — once the table exists, future
experiments (prompt-cache strategies, compaction thresholds, skill
loading orders) plug into the same schema.

**Quality-signal design (Contrarian-3 fix):**
User-satisfaction signal comes from ``agent/harness/scorer.py`` fitness
scores, NOT a hand-rolled heuristic. The ``harness_fitness_score`` column
is populated by a post-turn or offline harness batch job that joins on
``session_id``. We do NOT ship a ``suspected_retry`` boolean — previous
iteration's plan had no write-path for it and the signal would always
be FALSE. Harness is the real signal.

**Bucketing stickiness (user-request):**
Per-user (not per-thread) so a user stays on the same variant across all
their sessions — stronger measurement validity than zero-journey-per-user.

**Schema rationale:**
* ``id`` is a **client-generated UUID** (TEXT), not BIGSERIAL. The
  dispatcher creates it before the LLM call so the INSERT can be
  fire-and-forget without RETURNING — resolves Contrarian-2 hot-path DB
  latency finding (HDD-Postgres checkpoint spikes add 50-200ms TTFB
  otherwise).
* ``variant`` is an open-ended TEXT so future experiments can use their
  own variant names (e.g. ``"cache_strategy_a"``, ``"cache_strategy_b"``).
* ``experiment_id`` defaults to the active experiment name — different
  experiments share the table but are filterable.

Retention: experiment data is ephemeral — prune rows older than 90 days
via a scheduled DELETE (Phase-C cleanup task or pg_partman). Not enforced
by this migration.

Revision ID: 025_agent_ab_experiments
Revises: 024_agent_sessions_title
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "025_agent_ab_experiments"
down_revision = "024_agent_sessions_title"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "ab_experiments",
        sa.Column("id", sa.Text(), primary_key=True),  # client-generated UUID
        sa.Column(
            "experiment_id",
            sa.Text(),
            nullable=False,
            server_default="phase-c-hybrid-loop",
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),  # FK-logical to agent.sessions
        sa.Column("variant", sa.Text(), nullable=False),  # 'langgraph' | 'simple' | ...
        sa.Column("bucket_hash", sa.SmallInteger(), nullable=False),  # 0-99 audit trail
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column("turns_used", sa.Integer(), nullable=True),
        sa.Column("finished_naturally", sa.Boolean(), nullable=True),
        sa.Column("fallback_triggered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error", sa.Text(), nullable=True),
        # Harness-provided quality signal (Contrarian-3 resolution).
        # NULL until harness/scorer.py batch-job joins on session_id.
        sa.Column("harness_fitness_score", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("harness_eval_id", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ab_experiments_variant",
        "ab_experiments",
        ["experiment_id", "variant", "started_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ab_experiments_user_variant",
        "ab_experiments",
        ["user_id", "variant"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ab_experiments_session",
        "ab_experiments",
        ["session_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_ab_experiments_started_at",
        "ab_experiments",
        ["started_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ab_experiments_started_at", "ab_experiments", schema=SCHEMA,
    )
    op.drop_index(
        "ix_ab_experiments_session", "ab_experiments", schema=SCHEMA,
    )
    op.drop_index(
        "ix_ab_experiments_user_variant", "ab_experiments", schema=SCHEMA,
    )
    op.drop_index(
        "ix_ab_experiments_variant", "ab_experiments", schema=SCHEMA,
    )
    op.drop_table("ab_experiments", schema=SCHEMA)
