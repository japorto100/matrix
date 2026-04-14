"""Add default_mode and default_reasoning_effort to user_llm_settings.

exec-19: default_mode replaces default_model as the primary UX concept.
  - 'auto': system selects model (openrouter/free or /auto based on credits)
  - 'manual': user explicitly picks a model
default_reasoning_effort: persisted per-user preference (low/medium/high).

Revision ID: 012
Revises: 011
"""

from alembic import op

revision = "012"
down_revision = "011"


def upgrade():
    op.execute("""
        ALTER TABLE agent.user_llm_settings
        ADD COLUMN IF NOT EXISTS default_mode VARCHAR(20) DEFAULT 'auto',
        ADD COLUMN IF NOT EXISTS default_reasoning_effort VARCHAR(20) DEFAULT 'medium'
    """)


def downgrade():
    op.execute("""
        ALTER TABLE agent.user_llm_settings
        DROP COLUMN IF EXISTS default_mode,
        DROP COLUMN IF EXISTS default_reasoning_effort
    """)
