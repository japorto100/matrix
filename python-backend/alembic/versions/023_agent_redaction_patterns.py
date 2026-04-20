"""agent.redaction_patterns — Tier-2 DB-backed custom secret-patterns.

exec-security Phase-B P3 ships Tier-1 redaction (36 static prefix patterns
+ 8 pattern-classes in ``agent/security/redact.py``, snapshot-at-import,
sync-safe for the ``PostgresSpanProcessor.on_end`` hook). That covers the
industry-standard secret shapes shipped by hermes.

Tier-2 is org-specific extensions admins add at runtime — internal API-key
prefixes, customer-PII shapes, anything org-policy mandates. Separate
consumer-process (``agent/security/redact_consumer.py``) picks rows up and
applies them to spans post-INSERT. Default disabled via
``MATRIX_REDACT_CONSUMER_ENABLED=true`` env so the table can ship empty.

Schema:

* ``pattern_regex`` — validated via ``re.compile()`` at INSERT-endpoint
  time. ReDoS defense is in the consumer (100ms per-match timeout).
* ``replacement`` — substitution token; defaults to ``[REDACTED]``.
* ``severity`` — ``info``/``warn``/``critical`` for dashboard filtering.
* ``org_scope`` — ``NULL`` = applies to all orgs; scoped patterns limit
  to one tenant (multi-tenant future-proofing per matrix's enterprise
  translation-rule).
* ``is_active`` — toggle without delete so historical redactions stay
  attributable.

Retention:
Custom-pattern rows are long-lived (policy-table). No automatic prune.
Admins CRUD via a future REST endpoint in ``exec-security.md §1.3``.

Revision ID: 023_agent_redaction_patterns
Revises: 022_agent_sync_failures
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "023_agent_redaction_patterns"
down_revision = "022_agent_sync_failures"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "redaction_patterns",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pattern_regex", sa.Text(), nullable=False),
        sa.Column(
            "replacement",
            sa.Text(),
            nullable=False,
            server_default="[REDACTED]",
        ),
        sa.Column(
            "severity",
            sa.Text(),
            nullable=False,
            server_default="info",
        ),
        sa.Column("org_scope", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "severity IN ('info', 'warn', 'critical')",
            name="ck_redaction_patterns_severity",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_redaction_patterns_active_org",
        "redaction_patterns",
        ["is_active", "org_scope"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_redaction_patterns_active_org",
        "redaction_patterns",
        schema=SCHEMA,
    )
    op.drop_table("redaction_patterns", schema=SCHEMA)
