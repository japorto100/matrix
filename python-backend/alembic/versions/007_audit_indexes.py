"""Add performance indexes to agent.audit_events for Control Surface queries.

Slice 6 AuditTab supports filtering by action + user + role + date range +
success. This migration adds indexes so the query doesn't table-scan.

Revision ID: 007
Revises: 006
Create Date: 2026-04-07
"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "agent"


def upgrade() -> None:
    # Timestamp descending — common sort for "recent events first"
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_audit_timestamp_desc "
        f"ON {SCHEMA}.audit_events (timestamp DESC)"
    )
    # Action filter
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_audit_action ON {SCHEMA}.audit_events (action)"
    )
    # Composite user+action (for per-user activity views)
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_audit_user_action "
        f"ON {SCHEMA}.audit_events (user_id, action)"
    )
    # Composite role+action (for per-role views)
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_audit_role_action "
        f"ON {SCHEMA}.audit_events (agent_role, action)"
    )
    # Success filter (for error-only views)
    op.execute(
        f"CREATE INDEX IF NOT EXISTS ix_audit_success ON {SCHEMA}.audit_events (success)"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.ix_audit_success")
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.ix_audit_role_action")
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.ix_audit_user_action")
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.ix_audit_action")
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.ix_audit_timestamp_desc")
