"""ingestion.source_artifacts — durable provenance records for ingested sources.

Feature 021 separates source ingestion from retrieval and KG promotion. This
table records the authoritative source metadata for local files, papers, URLs
and future API payloads. Chunks, embeddings and KG proposals remain rebuildable
projections that reference the source artifact.

Revision ID: 031_ingestion_source_artifacts
Revises: 030_global_kg_bitemporal_claims
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "031_ingestion_source_artifacts"
down_revision = "030_global_kg_bitemporal_claims"
branch_labels = None
depends_on = None

SCHEMA = "ingestion"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ingestion")
    op.create_table(
        "source_artifacts",
        sa.Column("source_artifact_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False, server_default="local_file"),
        sa.Column("fetch_method", sa.Text(), nullable=False, server_default="local"),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("parser_name", sa.Text(), nullable=True),
        sa.Column("parser_version", sa.Text(), nullable=True),
        sa.Column("chunker_name", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("embedding_provider", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("valid_to", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
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
    op.create_index(
        "ix_source_artifacts_content_hash",
        "source_artifacts",
        ["content_hash"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_source_artifacts_source_uri",
        "source_artifacts",
        ["source_uri"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ux_source_artifacts_uri_hash",
        "source_artifacts",
        ["source_uri", "content_hash"],
        unique=True,
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_source_artifacts_uri_hash",
        "source_artifacts",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ix_source_artifacts_source_uri",
        "source_artifacts",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ix_source_artifacts_content_hash",
        "source_artifacts",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("source_artifacts", schema=SCHEMA, if_exists=True)
