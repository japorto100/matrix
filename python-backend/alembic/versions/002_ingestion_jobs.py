"""Create ingestion.jobs table for the ingestion worker (Slice 2 backend, exec-15 §5.2).

Revision ID: 002
Revises: 001
Create Date: 2026-04-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "ingestion"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "jobs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("file_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pipeline", sa.Text, nullable=False),
        sa.Column("user_id", sa.Text, nullable=False, server_default="local"),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("progress", sa.Float, server_default="0"),
        sa.Column("chunks_total", sa.Integer, nullable=True),
        sa.Column("chunks_done", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_hash", sa.Text, nullable=True),
        sa.Column(
            "metadata",
            sa.dialects.postgresql.JSONB,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema=SCHEMA,
    )

    op.create_index("ix_jobs_status", "jobs", ["status"], schema=SCHEMA)
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"], schema=SCHEMA)
    op.create_index("ix_jobs_document_hash", "jobs", ["document_hash"], schema=SCHEMA)
    op.create_index("ix_jobs_file_id", "jobs", ["file_id"], schema=SCHEMA)
    op.create_index("ix_jobs_started_at", "jobs", ["started_at"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_jobs_started_at", "jobs", schema=SCHEMA)
    op.drop_index("ix_jobs_file_id", "jobs", schema=SCHEMA)
    op.drop_index("ix_jobs_document_hash", "jobs", schema=SCHEMA)
    op.drop_index("ix_jobs_user_id", "jobs", schema=SCHEMA)
    op.drop_index("ix_jobs_status", "jobs", schema=SCHEMA)
    op.drop_table("jobs", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
