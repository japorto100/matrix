"""exec-16: User LLM Settings + Encrypted Credentials

Revision ID: 009
Revises: 008
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_llm_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False, unique=True),
        sa.Column("default_model", sa.Text, server_default="claude-sonnet"),
        sa.Column("per_role_overrides", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="agent",
    )

    op.create_table(
        "user_credentials",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False),  # llm, exchange, datasource
        sa.Column("provider_id", sa.Text, nullable=False),  # anthropic, openrouter, binance
        sa.Column("credential_enc", sa.LargeBinary, nullable=False),  # AES-256-GCM encrypted
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("is_valid", sa.Boolean, server_default=sa.text("true")),
        sa.Column("validated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "category", "provider_id"),
        schema="agent",
    )

    op.create_index("ix_user_credentials_user", "user_credentials", ["user_id"], schema="agent")
    op.create_index("ix_user_credentials_category", "user_credentials", ["category"], schema="agent")


def downgrade() -> None:
    op.drop_table("user_credentials", schema="agent")
    op.drop_table("user_llm_settings", schema="agent")
