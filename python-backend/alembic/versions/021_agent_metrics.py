"""agent.metrics — time-series store for scheduled metric rollups.

Scheduler-Phase-1 deferred the `metric_rollup` infra handler because
`agent.metrics` did not exist. This migration creates the table so the
handler can be enabled (Phase-2 prerequisite, but cheap enough to land
now).

Schema:

- ``(name, bucket_ts)`` is the primary key — one row per metric per
  time-bucket. bucket_ts is epoch-ms, truncated by the rollup-job's
  interval (hourly, daily) before insert.
- ``labels JSONB`` holds arbitrary Prometheus-style dimensions
  (e.g. ``{"role":"trader","model":"claude-sonnet-4-6"}``).
- ``kind`` disambiguates counter/gauge/histogram semantics for
  consumers; the rollup handler writes the pre-aggregated value.

Revision ID: 021_agent_metrics
Revises: 020_scheduler_cap_trigger_fix
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "021_agent_metrics"
down_revision = "020_scheduler_cap_trigger_fix"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "metrics",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("bucket_ts", sa.BigInteger(), nullable=False),
        sa.Column(
            "kind",
            sa.Text(),
            nullable=False,
            server_default="gauge",
        ),
        # gauge | counter | histogram_sum | histogram_count
        sa.Column(
            "value",
            sa.Numeric(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("labels", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("name", "bucket_ts"),
        sa.CheckConstraint(
            "kind IN ('gauge', 'counter', 'histogram_sum', 'histogram_count')",
            name="ck_metrics_kind",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_metrics_name_ts",
        "metrics",
        ["name", sa.text("bucket_ts DESC")],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_metrics_bucket",
        "metrics",
        ["bucket_ts"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_metrics_bucket", "metrics", schema=SCHEMA)
    op.drop_index("ix_metrics_name_ts", "metrics", schema=SCHEMA)
    op.drop_table("metrics", schema=SCHEMA)
