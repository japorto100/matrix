"""scheduler.scheduled_tasks + scheduler.task_executions (exec-scheduler Phase-1).

Eigenes ``scheduler`` Schema (separat von ``agent``) für River-koexistenz:
Alembic besitzt ``scheduled_tasks`` + ``task_executions``, River besitzt
``river_job`` / ``river_leader`` / ``river_migration`` im selben Schema
(konfiguriert via River's ``Schema`` Option in Go).

Konvention-Notes:
- ``BigInteger`` für Timestamps (epoch-ms) — konsistent mit 017/018.
- ``user_id TEXT`` (kein FK auf agent.users um cross-schema FK zu vermeiden,
  Rate-Limit-Trigger prüft nur auf ``scheduler.scheduled_tasks``).
- Hard-Cap 50 active tasks per user via BEFORE-INSERT-Trigger — DoS-Schutz
  gegen prompt-injected "add 1000 tasks". Soft-Cap 10 wird im Agent-Tool
  enforced (admin-überschreibbar via ``agent.user_llm_settings``).
- ``source`` trackt Entry-Surface (chat_agent / matrix_dm / api / system / ...)
  für Analytics. ``kind`` trackt Trigger-Typ (recurring / one_shot / ... ).
- ``tz`` speichert User-Timezone (IANA, z.B. ``Europe/Zurich``) — ``cron_expr``
  selbst ist TZ-neutral, River evaluiert mit ``time.Location``.
- ``delivery_target`` JSONB Shapes (formalisiert):
  * ``{"kind":"matrix_room","id":"!abc:server","room_type":"dm"|"group"}``
  * ``{"kind":"matrix_dm","user_id":"@u:server"}``
  * ``{"kind":"email","to":"..."}``
  * ``{"kind":"telegram","chat_id":"..."}``

Revision ID: 019_scheduler_schema
Revises: 018_components
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "019_scheduler_schema"
down_revision = "018_components"
branch_labels = None
depends_on = None

SCHEMA = "scheduler"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "scheduled_tasks",
        sa.Column("task_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        # chat_agent | chat_matrix_dm | chat_matrix_group | api
        # | github_webhook | system
        sa.Column("kind", sa.Text(), nullable=False),
        # recurring | one_shot | reminder | routine | condition | infra
        sa.Column("cron_expr", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.BigInteger(), nullable=True),
        sa.Column("tz", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column(
            "skill_ids", postgresql.ARRAY(sa.Text()), nullable=True
        ),
        sa.Column(
            "delivery_target", postgresql.JSONB(), nullable=True
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="active",
        ),
        # active | paused | completed | cancelled | errored
        sa.Column("max_executions", sa.Integer(), nullable=True),
        sa.Column(
            "execution_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("next_run_at", sa.BigInteger(), nullable=True),
        sa.Column("last_run_at", sa.BigInteger(), nullable=True),
        sa.Column("last_output_ref", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "(kind IN ('recurring', 'routine', 'condition', 'infra') AND "
            "cron_expr IS NOT NULL) "
            "OR (kind IN ('one_shot', 'reminder') AND scheduled_at IS NOT NULL)",
            name="ck_scheduled_tasks_trigger_fields",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'completed', "
            "'cancelled', 'errored')",
            name="ck_scheduled_tasks_status",
        ),
        sa.CheckConstraint(
            "kind IN ('recurring', 'one_shot', 'reminder', "
            "'routine', 'condition', 'infra')",
            name="ck_scheduled_tasks_kind",
        ),
        sa.CheckConstraint(
            "source IN ('chat_agent', 'chat_matrix_dm', "
            "'chat_matrix_group', 'api', 'github_webhook', 'system')",
            name="ck_scheduled_tasks_source",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_scheduled_tasks_user_status",
        "scheduled_tasks",
        ["user_id", "status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_scheduled_tasks_next_run",
        "scheduled_tasks",
        ["next_run_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_scheduled_tasks_kind_status",
        "scheduled_tasks",
        ["kind", "status"],
        schema=SCHEMA,
    )

    op.create_table(
        "task_executions",
        sa.Column("execution_id", sa.Text(), primary_key=True),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("started_at", sa.BigInteger(), nullable=False),
        sa.Column("completed_at", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default="running",
        ),
        # running | completed | failed | cancelled | timeout
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("output_ref", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_id"],
            [f"{SCHEMA}.scheduled_tasks.task_id"],
            ondelete="CASCADE",
            name="fk_task_executions_task",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', "
            "'cancelled', 'timeout')",
            name="ck_task_executions_status",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_task_executions_task_started",
        "task_executions",
        ["task_id", sa.text("started_at DESC")],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_task_executions_trace",
        "task_executions",
        ["trace_id"],
        schema=SCHEMA,
        postgresql_where=sa.text("trace_id IS NOT NULL"),
    )

    # Hard-Cap 50 active tasks per user (DoS-Schutz). Soft-Cap 10 wird
    # im Agent-Tool geprüft. BEFORE-INSERT-Trigger damit der Fehler
    # deterministisch am DB-Layer gemeldet wird, auch wenn der
    # Agent-Tool-Check umgangen wird.
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

    # NOTIFY-Channel für Hot-Reload des Go-seitigen cron_registry.
    # Go subscribt via `LISTEN scheduler_task_changed`, lädt die geänderte
    # Row neu und aktualisiert die PeriodicJob-Registration.
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.notify_task_changed()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'scheduler_task_changed',
                json_build_object(
                    'task_id', COALESCE(NEW.task_id, OLD.task_id),
                    'op', TG_OP,
                    'status',
                        COALESCE(NEW.status, OLD.status)
                )::text
            );
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_scheduled_tasks_notify
        AFTER INSERT OR UPDATE OR DELETE ON {SCHEMA}.scheduled_tasks
        FOR EACH ROW
        EXECUTE FUNCTION {SCHEMA}.notify_task_changed();
        """
    )


def downgrade() -> None:
    op.execute(
        f"DROP TRIGGER IF EXISTS trg_scheduled_tasks_notify "
        f"ON {SCHEMA}.scheduled_tasks"
    )
    op.execute(
        f"DROP FUNCTION IF EXISTS {SCHEMA}.notify_task_changed()"
    )
    op.execute(
        f"DROP TRIGGER IF EXISTS trg_scheduled_tasks_active_limit "
        f"ON {SCHEMA}.scheduled_tasks"
    )
    op.execute(
        f"DROP FUNCTION IF EXISTS {SCHEMA}.check_active_limit()"
    )
    op.drop_index(
        "ix_task_executions_trace",
        "task_executions",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_task_executions_task_started",
        "task_executions",
        schema=SCHEMA,
    )
    op.drop_table("task_executions", schema=SCHEMA)
    op.drop_index(
        "ix_scheduled_tasks_kind_status",
        "scheduled_tasks",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_scheduled_tasks_next_run",
        "scheduled_tasks",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_scheduled_tasks_user_status",
        "scheduled_tasks",
        schema=SCHEMA,
    )
    op.drop_table("scheduled_tasks", schema=SCHEMA)
    # Drop scheduler schema only if empty — River tables may still live
    # there. Guarded with RESTRICT so we don't accidentally nuke River.
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
