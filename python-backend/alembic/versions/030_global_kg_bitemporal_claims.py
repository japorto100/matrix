"""agent.global_kg_* — bitemporal global/domain KG claim store.

Feature 017 owns global/domain KG claims for trading, geopolitical and
world-model knowledge. This schema keeps it separate from agent memory
(Hindsight KG-like memory, MemPalace loci, Personal KB) while still allowing
those systems to propose claims through explicit evidence refs.

Design notes:
- `valid_period` is business time: when a claim is considered true/valid.
- `sys_from/sys_to` is system time: when Matrix knew this version.
- Current truth is `sys_to = 'infinity'` plus status/lane policy.
- `conflict_key` is the conservative overlap key. Application code computes it
  from canonical subject/predicate/object identity, so inserts remain append-only
  instead of relying on lossy split/truncate triggers.
- `projection_outbox` is rebuildable and targets NornicDB/nonicdb first.

Revision ID: 030_global_kg_bitemporal_claims
Revises: 029_mempalace_pgvector_drawers
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "030_global_kg_bitemporal_claims"
down_revision = "029_mempalace_pgvector_drawers"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS agent")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "kg_entities",
        sa.Column("entity_id", sa.Text(), primary_key=True),
        sa.Column("canonical_key", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column(
            "names",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "provenance",
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
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
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
    op.execute(
        "ALTER TABLE agent.kg_entities ALTER COLUMN embedding TYPE vector USING embedding::vector"
    )
    op.create_index(
        "ux_kg_entities_canonical_key",
        "kg_entities",
        ["canonical_key"],
        unique=True,
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_kg_entities_type",
        "kg_entities",
        ["entity_type"],
        schema=SCHEMA,
        if_not_exists=True,
    )

    op.create_table(
        "kg_claims",
        sa.Column("claim_id", sa.Text(), primary_key=True),
        sa.Column("conflict_key", sa.Text(), nullable=False),
        sa.Column("subject_entity_id", sa.Text(), nullable=False),
        sa.Column("predicate", sa.Text(), nullable=False),
        sa.Column("object_entity_id", sa.Text(), nullable=True),
        sa.Column(
            "object_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column(
            "lane",
            sa.Text(),
            nullable=False,
            server_default="fast",
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="proposed",
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valid_period", postgresql.TSTZRANGE(), nullable=False),
        sa.Column(
            "sys_from",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "sys_to",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("'infinity'::timestamptz"),
        ),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
        sa.Column("ttl_seconds", sa.BigInteger(), nullable=True),
        sa.Column("validator_version", sa.Text(), nullable=True),
        sa.Column("validator_score", sa.Float(), nullable=True),
        sa.Column(
            "provenance",
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
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["subject_entity_id"],
            [f"{SCHEMA}.kg_entities.entity_id"],
            ondelete="RESTRICT",
            name="fk_kg_claims_subject",
        ),
        sa.ForeignKeyConstraint(
            ["object_entity_id"],
            [f"{SCHEMA}.kg_entities.entity_id"],
            ondelete="RESTRICT",
            name="fk_kg_claims_object",
        ),
        sa.CheckConstraint(
            "lane IN ('fast', 'slow')",
            name="ck_kg_claims_lane",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'promoted', 'rejected', 'superseded')",
            name="ck_kg_claims_status",
        ),
        sa.CheckConstraint(
            "object_entity_id IS NOT NULL OR object_value IS NOT NULL",
            name="ck_kg_claims_object_present",
        ),
        sa.CheckConstraint(
            "lower(valid_period) < upper(valid_period)",
            name="ck_kg_claims_valid_period_non_empty",
        ),
        sa.CheckConstraint(
            "sys_from < sys_to",
            name="ck_kg_claims_sys_period_non_empty",
        ),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.execute(
        "ALTER TABLE agent.kg_claims ALTER COLUMN embedding TYPE vector USING embedding::vector"
    )
    op.execute(
        """
        ALTER TABLE agent.kg_claims
        ADD COLUMN IF NOT EXISTS sys_period tstzrange
        GENERATED ALWAYS AS (tstzrange(sys_from, sys_to, '[)')) STORED
        """
    )
    op.create_index(
        "ix_kg_claims_subject_predicate",
        "kg_claims",
        ["subject_entity_id", "predicate"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_kg_claims_status_lane",
        "kg_claims",
        ["status", "lane"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_kg_claims_valid_period",
        "kg_claims",
        ["valid_period"],
        schema=SCHEMA,
        postgresql_using="gist",
        if_not_exists=True,
    )
    op.create_index(
        "ix_kg_claims_embedding_model_dim",
        "kg_claims",
        ["embedding_model", "embedding_dim"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.execute(
        """
        ALTER TABLE agent.kg_claims
        ADD CONSTRAINT ex_kg_claims_current_conflict
        EXCLUDE USING gist (
            conflict_key WITH =,
            valid_period WITH &&
        )
        WHERE (
            sys_to = 'infinity'::timestamptz
            AND status IN ('proposed', 'promoted')
        )
        """
    )

    op.create_table(
        "kg_claim_evidence",
        sa.Column("evidence_id", sa.Text(), primary_key=True),
        sa.Column("claim_id", sa.Text(), nullable=False),
        sa.Column("source_layer", sa.Text(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["claim_id"],
            [f"{SCHEMA}.kg_claims.claim_id"],
            ondelete="CASCADE",
            name="fk_kg_claim_evidence_claim",
        ),
        sa.CheckConstraint(
            "source_layer IN ('memory_fusion', 'personal_kb', 'world_evidence', 'ingestion', 'manual')",
            name="ck_kg_claim_evidence_source_layer",
        ),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_kg_claim_evidence_claim",
        "kg_claim_evidence",
        ["claim_id"],
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_kg_claim_evidence_source_ref",
        "kg_claim_evidence",
        ["source_layer", "source_ref"],
        schema=SCHEMA,
        if_not_exists=True,
    )

    op.create_table(
        "kg_claim_access_stats",
        sa.Column("claim_id", sa.Text(), primary_key=True),
        sa.Column("access_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_accessed", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            [f"{SCHEMA}.kg_claims.claim_id"],
            ondelete="CASCADE",
            name="fk_kg_claim_access_stats_claim",
        ),
        schema=SCHEMA,
        if_not_exists=True,
    )

    op.create_table(
        "kg_projection_outbox",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("claim_id", sa.Text(), nullable=False),
        sa.Column(
            "projection_target",
            sa.Text(),
            nullable=False,
            server_default="nornicdb",
        ),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            [f"{SCHEMA}.kg_claims.claim_id"],
            ondelete="CASCADE",
            name="fk_kg_projection_outbox_claim",
        ),
        sa.CheckConstraint(
            "projection_target IN ('nornicdb')",
            name="ck_kg_projection_outbox_target",
        ),
        sa.CheckConstraint(
            "operation IN ('upsert_entity', 'upsert_claim', 'delete_claim', 'rebuild')",
            name="ck_kg_projection_outbox_operation",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'done', 'failed')",
            name="ck_kg_projection_outbox_status",
        ),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_kg_projection_outbox_pending",
        "kg_projection_outbox",
        ["projection_target", "status", sa.text("created_at ASC")],
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_kg_projection_outbox_pending",
        "kg_projection_outbox",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("kg_projection_outbox", schema=SCHEMA, if_exists=True)
    op.drop_table("kg_claim_access_stats", schema=SCHEMA, if_exists=True)
    op.drop_index(
        "ix_kg_claim_evidence_source_ref",
        "kg_claim_evidence",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ix_kg_claim_evidence_claim",
        "kg_claim_evidence",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("kg_claim_evidence", schema=SCHEMA, if_exists=True)
    op.execute(
        "ALTER TABLE IF EXISTS agent.kg_claims DROP CONSTRAINT IF EXISTS ex_kg_claims_current_conflict"
    )
    op.drop_index(
        "ix_kg_claims_embedding_model_dim",
        "kg_claims",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ix_kg_claims_valid_period",
        "kg_claims",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ix_kg_claims_status_lane",
        "kg_claims",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ix_kg_claims_subject_predicate",
        "kg_claims",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("kg_claims", schema=SCHEMA, if_exists=True)
    op.drop_index(
        "ix_kg_entities_type",
        "kg_entities",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_index(
        "ux_kg_entities_canonical_key",
        "kg_entities",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("kg_entities", schema=SCHEMA, if_exists=True)
