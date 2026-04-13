"""Create agent.skills_state for persisted skill toggles.

Revision ID: 008_skills_state
Revises: 007_audit_indexes
Create Date: 2026-04-09
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "008_skills_state"
down_revision = "007_audit_indexes"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "skills_state",
        sa.Column("skill_id", sa.Text(), nullable=False),
        sa.Column(
            "user_id", sa.Text(), nullable=False, server_default=sa.text("'local'")
        ),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("updated_by", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("skill_id", "user_id", name="pk_skills_state"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_skills_state_user_id",
        "skills_state",
        ["user_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_skills_state_user_id", table_name="skills_state", schema=SCHEMA)
    op.drop_table("skills_state", schema=SCHEMA)
