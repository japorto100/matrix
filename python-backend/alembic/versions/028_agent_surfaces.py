"""agent.agent_surfaces — A2UI widget-surface persistence (plan-v2 Phase-2 #31).

Backs the client-side ``usePersistentSurface`` hook with a server-side
store so A2UI widgets carry across devices / browsers / origins. Until
this migration, ``frontend_merger/src/features/agent/hooks/
usePersistentSurface.ts`` was localStorage-only (Phase-1).

Schema rationale:

* ``user_id`` (text, FK-less) — owner of the surface. Scoped by Matrix
  user MXID as delivered via the ``X-Actor-User-Id`` header on the
  go-appservice route. FK-less because the matrix user-space lives
  outside agent schema.
* ``surface_id`` (text) — logical surface identifier ("main", chat-inline
  surface-ids, etc.) chosen by the client. Opaque to the server.
* ``schema_version`` (int) — envelope version the client wrote; server
  is content-agnostic but persists for forward-compat.
* ``surface_json`` (jsonb) — the A2UI widget-spec blob. JSONB rather
  than TEXT because Ansatz-X live-updates (exec-09 Phase-2 #32) will
  want partial-path updates later and jsonb supports that cheaply.
* ``updated_at`` (timestamptz, default now()) — last-write wins across
  devices; no optimistic concurrency needed at this phase (single-user
  writes are infrequent relative to SSE pushes).

Primary key is the pair ``(user_id, surface_id)`` — one row per user
per surface. Clients upsert on save, read by pair on load, and delete
when a surface is explicitly cleared.

Cross-ref: ``specs/execution/exec-09-protocols-generative-ui.md``,
``docs/superpowers/plans/2026-04-21-ag-stack-frontend-merger-plan-v2.md
§Phase-2``.

Revision ID: 028_agent_surfaces
Revises: 027_ab_experiments_routing_dim
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "028_agent_surfaces"
down_revision = "027_ab_experiments_routing_dim"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.create_table(
        "agent_surfaces",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("surface_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "surface_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "surface_id"),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_index(
        "ix_agent_surfaces_user",
        "agent_surfaces",
        ["user_id"],
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_surfaces_user",
        "agent_surfaces",
        schema=SCHEMA,
        if_exists=True,
    )
    op.drop_table("agent_surfaces", schema=SCHEMA, if_exists=True)
