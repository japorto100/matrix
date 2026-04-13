"""Add selected_models jsonb to user_llm_settings.

exec-19 Stufe 5b: User selects which models appear in agent-chat Model-Picker.
Stored as a JSON array of model ID strings.

Revision ID: 011
Revises: 010
"""

from alembic import op

revision = "011"
down_revision = "010"


def upgrade():
    op.execute("""
        ALTER TABLE agent.user_llm_settings
        ADD COLUMN IF NOT EXISTS selected_models JSONB DEFAULT '[]'::jsonb
    """)


def downgrade():
    op.execute("""
        ALTER TABLE agent.user_llm_settings
        DROP COLUMN IF EXISTS selected_models
    """)
