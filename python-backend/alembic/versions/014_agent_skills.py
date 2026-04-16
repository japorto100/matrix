"""agent_skills + user_skill_preferences (exec-skills / exec-18).

Revision ID: 014_agent_skills
Revises: 013
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "014_agent_skills"
down_revision = "013"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "agent_skills",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "tier",
            sa.Text(),
            nullable=False,
            server_default="global",
        ),
        sa.Column("owner_id", sa.Text(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parent_skill_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_from_session", sa.Text(), nullable=True),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("api_version", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_skill_id"],
            [f"{SCHEMA}.agent_skills.id"],
            name="fk_agent_skills_parent",
            ondelete="SET NULL",
            use_alter=True,
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_skills_name",
        "agent_skills",
        ["name"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_skills_tier",
        "agent_skills",
        ["tier"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "user_skill_preferences",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("user_id", "skill_id", name="pk_user_skill_preferences"),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            [f"{SCHEMA}.agent_skills.id"],
            name="fk_user_skill_preferences_skill",
            ondelete="CASCADE",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_user_skill_preferences_user",
        "user_skill_preferences",
        ["user_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_skill_preferences_user",
        table_name="user_skill_preferences",
        schema=SCHEMA,
    )
    op.drop_table("user_skill_preferences", schema=SCHEMA)
    op.drop_index("ix_agent_skills_tier", table_name="agent_skills", schema=SCHEMA)
    op.drop_index("ix_agent_skills_name", table_name="agent_skills", schema=SCHEMA)
    op.drop_table("agent_skills", schema=SCHEMA)
