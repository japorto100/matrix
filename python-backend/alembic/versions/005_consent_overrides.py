"""Create agent.consent_overrides for D2 DB Overlay + Hot-Reload pattern.

Defaults come from agent/consent_policy.yaml (read at startup).
DB overlays are per (role_id, category_id, user_id) and win over yaml.
ConsentProvider has 5s TTL cache; /api/v1/control/permissions/reload clears it.

Revision ID: 005
Revises: 004
Create Date: 2026-04-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "consent_overrides",
        sa.Column("role_id", sa.Text, nullable=False),
        sa.Column("category_id", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text, nullable=False, server_default="local"),
        sa.Column("level", sa.Text, nullable=False),  # auto|inform|confirm|deny
        sa.Column("updated_by", sa.Text, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("role_id", "category_id", "user_id"),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_consent_overrides_user",
        "consent_overrides",
        ["user_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_consent_overrides_user", "consent_overrides", schema=SCHEMA)
    op.drop_table("consent_overrides", schema=SCHEMA)
