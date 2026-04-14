"""Add utility_models jsonb to user_llm_settings.

exec-19: User configures which models to use for utility tasks
(summarizer, embedder, reranker, stt, tts).
Stored as a JSON object: {"summarizer": "model-id", "stt": "model-id", ...}

Revision ID: 013
Revises: 012
"""

from alembic import op

revision = "013"
down_revision = "012"


def upgrade():
    op.execute("""
        ALTER TABLE agent.user_llm_settings
        ADD COLUMN IF NOT EXISTS utility_models JSONB DEFAULT '{}'::jsonb
    """)


def downgrade():
    op.execute("""
        ALTER TABLE agent.user_llm_settings
        DROP COLUMN IF EXISTS utility_models
    """)
