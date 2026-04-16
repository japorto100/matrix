"""skill_type + assets columns on agent_skills (exec-skills Phase A).

skill_type: SkillRL §3.2 General always-load vs Task-Specific retrieval-gated.
assets: JSONB for scripts/examples/templates subdirectory content.

Revision ID: 015_skill_extensions
Revises: 014_agent_skills
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "015_skill_extensions"
down_revision = "014_agent_skills"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.add_column(
        "agent_skills",
        sa.Column(
            "skill_type",
            sa.Text(),
            nullable=False,
            server_default="task_specific",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_skills_skill_type",
        "agent_skills",
        ["skill_type"],
        schema=SCHEMA,
    )
    op.add_column(
        "agent_skills",
        sa.Column(
            "assets",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("agent_skills", "assets", schema=SCHEMA)
    op.drop_index(
        "ix_agent_skills_skill_type",
        table_name="agent_skills",
        schema=SCHEMA,
    )
    op.drop_column("agent_skills", "skill_type", schema=SCHEMA)
