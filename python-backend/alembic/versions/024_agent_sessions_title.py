"""agent.sessions — add title column (Phase-B P6).

Scheduler tasks, resumed conversations, and Control-UI session-lists all
want a short, searchable "what was this about" label per session.
`agent.sessions` (migration 016) does not have one, so matrix has been
falling back to the first user message truncated to N chars — noisy, hard
to scan, and not editable by the user.

P6 adds:

* ``agent.sessions.title TEXT`` — nullable; populated asynchronously
  after the first assistant turn by :mod:`agent.titles.generator`
* index ``(user_id, title)`` for Control-UI search

Rollback is safe — a ``DROP COLUMN`` on a nullable TEXT column doesn't
lose any pre-populated data because rollback implies the feature is
disabled at the code level, so nothing depends on the column value.

Revision ID: 024_agent_sessions_title
Revises: 023_agent_redaction_patterns
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "024_agent_sessions_title"
down_revision = "023_agent_redaction_patterns"
branch_labels = None
depends_on = None

SCHEMA = "agent"


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("title", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sessions_user_id_title",
        "sessions",
        ["user_id", "title"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sessions_user_id_title",
        "sessions",
        schema=SCHEMA,
    )
    op.drop_column("sessions", "title", schema=SCHEMA)
