"""Scheduler hard-cap trigger — fix bypass via pause+insert+resume.

Migration 019 installed ``check_active_limit()`` as BEFORE INSERT only.
A caller could insert 50 active tasks (cap hit), PATCH 30 to paused,
insert 30 more (count=50, under cap), then PATCH the original 30 back
to active — ending with 80 active tasks.

This migration switches the trigger to BEFORE INSERT OR UPDATE, with a
status-transition guard so UPDATEs that don't change status to 'active'
(e.g. pause or edit-prompt) still pass fast.

Revision ID: 020_scheduler_cap_trigger_fix
Revises: 019_scheduler_schema
"""

from __future__ import annotations

from alembic import op

revision = "020_scheduler_cap_trigger_fix"
down_revision = "019_scheduler_schema"
branch_labels = None
depends_on = None

SCHEMA = "scheduler"


def upgrade() -> None:
    # Drop the old INSERT-only trigger.
    op.execute(
        f"DROP TRIGGER IF EXISTS trg_scheduled_tasks_active_limit "
        f"ON {SCHEMA}.scheduled_tasks"
    )
    # Replace the function — body now gates on "is this row becoming
    # active?" rather than "is this an INSERT of an active row?".
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.check_active_limit()
        RETURNS TRIGGER AS $$
        DECLARE
            active_count INTEGER;
            becoming_active BOOLEAN;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                becoming_active := (NEW.status = 'active');
            ELSE
                -- UPDATE: only check when the row is newly flipping to
                -- active. Same-status updates (e.g. prompt edits) skip.
                becoming_active := (
                    NEW.status = 'active'
                    AND COALESCE(OLD.status, '') != 'active'
                );
            END IF;

            IF becoming_active THEN
                SELECT COUNT(*) INTO active_count
                FROM {SCHEMA}.scheduled_tasks
                WHERE user_id = NEW.user_id
                  AND status = 'active'
                  AND task_id <> NEW.task_id;
                IF active_count >= 50 THEN
                    RAISE EXCEPTION
                        'scheduled tasks hard-cap reached: user % has % active tasks',
                        NEW.user_id, active_count
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_scheduled_tasks_active_limit
        BEFORE INSERT OR UPDATE ON {SCHEMA}.scheduled_tasks
        FOR EACH ROW
        EXECUTE FUNCTION {SCHEMA}.check_active_limit();
        """
    )


def downgrade() -> None:
    op.execute(
        f"DROP TRIGGER IF EXISTS trg_scheduled_tasks_active_limit "
        f"ON {SCHEMA}.scheduled_tasks"
    )
    # Restore the 019 version (INSERT-only, includes NEW.task_id in count
    # which the bypass exploited — documented as a known limitation now).
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.check_active_limit()
        RETURNS TRIGGER AS $$
        DECLARE
            active_count INTEGER;
        BEGIN
            IF NEW.status = 'active' THEN
                SELECT COUNT(*) INTO active_count
                FROM {SCHEMA}.scheduled_tasks
                WHERE user_id = NEW.user_id
                  AND status = 'active';
                IF active_count >= 50 THEN
                    RAISE EXCEPTION
                        'scheduled tasks hard-cap reached: user % has % active tasks',
                        NEW.user_id, active_count
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_scheduled_tasks_active_limit
        BEFORE INSERT ON {SCHEMA}.scheduled_tasks
        FOR EACH ROW
        EXECUTE FUNCTION {SCHEMA}.check_active_limit();
        """
    )
