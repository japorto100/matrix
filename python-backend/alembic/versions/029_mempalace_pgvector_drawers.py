"""agent.mempalace_drawers — Postgres/pgvector MemPalace verbatim store.

Moves the Matrix MemPalace adapter off local Chroma/SQLite while preserving
upstream MemPalace concepts: wings, rooms, halls, closets, drawers, and raw
verbatim drawer content. Embedding vectors are stored in pgvector and tagged
with model+dimension so OpenRouter embedding models can be changed without
mixing incompatible vector dimensions during retrieval.

Revision ID: 029_mempalace_pgvector_drawers
Revises: 028_agent_surfaces
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "029_mempalace_pgvector_drawers"
down_revision = "028_agent_surfaces"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "mempalace_drawers",
        sa.Column("drawer_id", sa.Text(), primary_key=True),
        sa.Column("bank_id", sa.Text(), nullable=False),
        sa.Column("wing", sa.Text(), nullable=False),
        sa.Column("room", sa.Text(), nullable=False),
        sa.Column("hall", sa.Text(), nullable=False, server_default="misc"),
        sa.Column("closet_id", sa.Text(), nullable=False),
        sa.Column("loci_path", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("document_id", sa.Text(), nullable=True),
        sa.Column("source_file", sa.Text(), nullable=True),
        sa.Column("source_ref", sa.Text(), nullable=True),
        sa.Column("chunk_id", sa.Text(), nullable=True),
        sa.Column("fact_type", sa.Text(), nullable=False, server_default="experience"),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("embedding_dim", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.Text(), nullable=True),
        sa.Column(
            "filed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.execute(
        """
        ALTER TABLE agent.mempalace_drawers
        ALTER COLUMN embedding TYPE vector USING embedding::vector
        """
    )
    op.create_index(
        "ux_mempalace_drawers_bank_loci_hash",
        "mempalace_drawers",
        ["bank_id", "wing", "room", "content_hash"],
        unique=True,
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_mempalace_drawers_loci",
        "mempalace_drawers",
        ["bank_id", "wing", "room", "hall"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_mempalace_drawers_model_dim",
        "mempalace_drawers",
        ["embedding_model", "embedding_dim"],
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mempalace_drawers_model_dim",
        "mempalace_drawers",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ix_mempalace_drawers_loci",
        "mempalace_drawers",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ux_mempalace_drawers_bank_loci_hash",
        "mempalace_drawers",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("mempalace_drawers", schema=SCHEMA, if_exists=True)
