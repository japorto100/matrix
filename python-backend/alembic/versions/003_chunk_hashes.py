"""Create ingestion.chunk_hashes for hash-based incremental reindex.

Cursor IDE / paperwatcher manifest.py Pattern: per-chunk content hash, so that
re-ingesting a modified document only re-embeds the changed chunks.

Revision ID: 003
Revises: 002
Create Date: 2026-04-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "ingestion"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "chunk_hashes",
        sa.Column(
            "job_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_id", sa.Text, nullable=False),
        sa.Column("content_hash", sa.Text, nullable=False),
        sa.Column("doc_id", sa.Text, nullable=False),
        sa.Column("section", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("job_id", "chunk_id"),
        schema=SCHEMA,
    )

    op.create_index("ix_chunk_hashes_doc", "chunk_hashes", ["doc_id"], schema=SCHEMA)
    op.create_index("ix_chunk_hashes_content", "chunk_hashes", ["content_hash"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_chunk_hashes_content", "chunk_hashes", schema=SCHEMA)
    op.drop_index("ix_chunk_hashes_doc", "chunk_hashes", schema=SCHEMA)
    op.drop_table("chunk_hashes", schema=SCHEMA)
