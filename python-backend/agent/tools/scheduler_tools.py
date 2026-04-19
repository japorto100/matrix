"""Agent-facing scheduler tools (exec-scheduler §7.2).

Nine tools expose the full lifecycle without the chat-UI ever touching a
form:

* ``schedule_draft`` — parses natural-language intent to a draft; NO DB write.
* ``confirm_scheduled_task`` — persists a previously-drafted task.
* ``schedule_list`` — lists the user's scheduled tasks.
* ``schedule_pause`` — status → paused.
* ``schedule_resume`` — status → active.
* ``schedule_cancel`` — status → cancelled (soft-delete; row retained for history).
* ``schedule_list_runs`` — per-task execution history.
* ``schedule_edit`` — patch prompt / cron / delivery_target without recreate.
* ``schedule_run_now`` — manual one-off fire of an existing task.

Two-step flow (``schedule_draft`` → ``confirm_scheduled_task``) is
intentional: "morgen 9" is ambiguous in context; the agent echoes the
parsed draft back to the user and only the user's "ja" triggers the
INSERT.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from agent.scheduler import db as scheduler_db
from agent.scheduler import service_user_id  # noqa: F401 — re-exported hint
from agent.scheduler.nl_parser import draft_to_dict, parse
from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext

log = logging.getLogger(__name__)


# ── Pydantic input models ────────────────────────────────────────────────


class ScheduleDraftInput(BaseModel):
    natural_language: str = Field(
        min_length=1,
        description="User's scheduling intent, e.g. 'jeden Montag 9 Uhr "
        "Portfolio-Briefing'.",
    )
    user_tz: str = Field(
        default="UTC",
        description="IANA timezone for interpreting times (e.g. Europe/Zurich).",
    )


class ConfirmScheduledTaskInput(BaseModel):
    kind: str = Field(description="recurring | one_shot | reminder")
    cron_expr: str | None = Field(default=None, description="5-field cron; null for one-shot/reminder")
    scheduled_at_ms: int | None = Field(default=None, description="epoch-ms; null for recurring")
    tz: str = Field(default="UTC", description="IANA timezone")
    prompt: str = Field(min_length=1, description="The instruction the agent runs at fire-time")
    source: str = Field(
        default="chat_agent",
        description="chat_agent | chat_matrix_dm | chat_matrix_group | api",
    )
    delivery_target: dict | None = Field(
        default=None,
        description="{'kind':'matrix_room|matrix_dm|email|telegram', ...}",
    )
    skill_ids: list[str] | None = Field(
        default=None, description="Skill ids to bind at fire time"
    )
    max_executions: int | None = Field(
        default=None, description="Unlimited when null; 1 for one-shot"
    )


class ScheduleListInput(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)


class SchedulePauseInput(BaseModel):
    task_id: str = Field(min_length=1)


class ScheduleResumeInput(BaseModel):
    task_id: str = Field(min_length=1)


class ScheduleCancelInput(BaseModel):
    task_id: str = Field(min_length=1)


class ScheduleListRunsInput(BaseModel):
    task_id: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class ScheduleEditInput(BaseModel):
    task_id: str = Field(min_length=1)
    # All fields optional — only provided ones are updated. NOT editable:
    # user_id, source, kind. Changing kind means cancel + recreate.
    prompt: str | None = Field(default=None, min_length=1)
    cron_expr: str | None = None
    scheduled_at_ms: int | None = None
    tz: str | None = None
    delivery_target: dict | None = None
    max_executions: int | None = None


class ScheduleRunNowInput(BaseModel):
    task_id: str = Field(min_length=1)


# ── Tool implementations ──────────────────────────────────────────────────


class ScheduleDraftTool(TradingTool):
    """Parse natural-language scheduling intent into a draft for confirmation."""

    input_model = ScheduleDraftInput

    @property
    def name(self) -> str:
        return "schedule_draft"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Parse the user's natural-language scheduling request and return a "
                "structured draft (kind, cron_expr or scheduled_at_ms, tz, prompt). "
                "DOES NOT write to the database. Use this FIRST, echo the draft back "
                "to the user for confirmation, then call confirm_scheduled_task with "
                "the exact fields from this draft."
            ),
            "input_schema": ScheduleDraftInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = ScheduleDraftInput(**tool_input)
        draft = parse(params.natural_language, user_tz=params.user_tz)
        return {
            "ok": True,
            "draft": draft_to_dict(draft),
            "next_step": (
                "Echo the draft back to the user, wait for confirmation, "
                "then call confirm_scheduled_task with the same fields."
            ),
        }


class ConfirmScheduledTaskTool(TradingTool):
    """Persist a previously drafted scheduled task."""

    input_model = ConfirmScheduledTaskInput

    @property
    def name(self) -> str:
        return "confirm_scheduled_task"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Persist a scheduled task to the database. Call this ONLY after "
                "the user has confirmed a draft returned by schedule_draft. "
                "Returns the generated task_id on success."
            ),
            "input_schema": ConfirmScheduledTaskInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = ConfirmScheduledTaskInput(**tool_input)

        # Soft-cap check before INSERT — hard cap fires as trigger if this slips.
        active = await scheduler_db.count_active_for_user(ctx.user_id)
        soft_cap = 10
        if active >= soft_cap:
            return {
                "ok": False,
                "error": "soft_cap_reached",
                "message": (
                    f"You already have {active} active scheduled tasks "
                    f"(soft limit {soft_cap}). Pause or cancel some first."
                ),
            }

        row = scheduler_db.InsertTaskRow(
            user_id=ctx.user_id,
            source=params.source,
            kind=params.kind,
            cron_expr=params.cron_expr,
            scheduled_at_ms=params.scheduled_at_ms,
            tz=params.tz,
            prompt=params.prompt,
            skill_ids=params.skill_ids,
            delivery_target=params.delivery_target,
            max_executions=params.max_executions,
        )
        try:
            task_id = await scheduler_db.insert_task(row)
        except Exception as exc:  # noqa: BLE001 — surface DB errors to LLM
            log.warning("confirm_scheduled_task insert failed: %s", exc)
            return {"ok": False, "error": "insert_failed", "message": str(exc)}

        return {
            "ok": True,
            "task_id": task_id,
            "status": "active",
            "kind": params.kind,
        }


class ScheduleListTool(TradingTool):
    """List the user's scheduled tasks."""

    input_model = ScheduleListInput

    @property
    def name(self) -> str:
        return "schedule_list"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": "Return the user's scheduled tasks (all statuses).",
            "input_schema": ScheduleListInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = ScheduleListInput(**tool_input)
        tasks = await scheduler_db.list_tasks_for_user(
            ctx.user_id, limit=params.limit
        )
        return {"ok": True, "tasks": _dtos(tasks), "count": len(tasks)}


class SchedulePauseTool(TradingTool):
    input_model = SchedulePauseInput

    @property
    def name(self) -> str:
        return "schedule_pause"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": "Pause a scheduled task (status → paused). Can be resumed.",
            "input_schema": SchedulePauseInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = SchedulePauseInput(**tool_input)
        ok = await scheduler_db.patch_status(params.task_id, ctx.user_id, "paused")
        return {"ok": ok, "task_id": params.task_id, "status": "paused"}


class ScheduleResumeTool(TradingTool):
    input_model = ScheduleResumeInput

    @property
    def name(self) -> str:
        return "schedule_resume"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": "Resume a paused scheduled task (status → active).",
            "input_schema": ScheduleResumeInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = ScheduleResumeInput(**tool_input)
        ok = await scheduler_db.patch_status(params.task_id, ctx.user_id, "active")
        return {"ok": ok, "task_id": params.task_id, "status": "active"}


class ScheduleCancelTool(TradingTool):
    input_model = ScheduleCancelInput

    @property
    def name(self) -> str:
        return "schedule_cancel"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": "Cancel a scheduled task (status → cancelled). Soft delete — row retained for audit.",
            "input_schema": ScheduleCancelInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = ScheduleCancelInput(**tool_input)
        ok = await scheduler_db.patch_status(
            params.task_id, ctx.user_id, "cancelled"
        )
        return {"ok": ok, "task_id": params.task_id, "status": "cancelled"}


class ScheduleListRunsTool(TradingTool):
    input_model = ScheduleListRunsInput

    @property
    def name(self) -> str:
        return "schedule_list_runs"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": "Return past executions of a scheduled task (status, duration, summary).",
            "input_schema": ScheduleListRunsInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = ScheduleListRunsInput(**tool_input)
        # Ownership check: only surface runs for tasks the user owns.
        task = await scheduler_db.get_task(params.task_id)
        if task is None or task.get("user_id") != ctx.user_id:
            return {"ok": False, "error": "not_found"}
        runs = await scheduler_db.list_executions(params.task_id, limit=params.limit)
        return {"ok": True, "runs": runs, "count": len(runs)}


class ScheduleEditTool(TradingTool):
    """Edit fields of an existing scheduled task (prompt, schedule, delivery)."""

    input_model = ScheduleEditInput

    @property
    def name(self) -> str:
        return "schedule_edit"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Edit an existing scheduled task. Provide only the fields you "
                "want to change (prompt, cron_expr, scheduled_at_ms, tz, "
                "delivery_target, max_executions). Cannot change kind — to "
                "switch between recurring/one_shot/reminder, cancel and "
                "create a new task."
            ),
            "input_schema": ScheduleEditInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        params = ScheduleEditInput(**tool_input)
        ok = await scheduler_db.patch_task_fields(
            params.task_id,
            ctx.user_id,
            prompt=params.prompt,
            cron_expr=params.cron_expr,
            scheduled_at_ms=params.scheduled_at_ms,
            tz=params.tz,
            delivery_target=params.delivery_target,
            max_executions=params.max_executions,
        )
        if not ok:
            return {
                "ok": False,
                "error": "not_found_or_unauthorized",
                "task_id": params.task_id,
            }
        return {"ok": True, "task_id": params.task_id, "updated": True}


class ScheduleRunNowTool(TradingTool):
    """Fire a scheduled task immediately (testing / on-demand)."""

    input_model = ScheduleRunNowInput

    @property
    def name(self) -> str:
        return "schedule_run_now"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Fire a scheduled task RIGHT NOW (one-off manual trigger). "
                "The task's normal cron / scheduled_at continues unchanged. "
                "Useful for testing a prompt before relying on its schedule, "
                "or running a weekly task ad-hoc."
            ),
            "input_schema": ScheduleRunNowInput.model_json_schema(),
        }

    async def execute(
        self, tool_input: dict, ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        from agent.scheduler.publisher import FireContext, publish_fire

        params = ScheduleRunNowInput(**tool_input)
        task = await scheduler_db.get_task(params.task_id)
        if task is None or task.get("user_id") != ctx.user_id:
            return {"ok": False, "error": "not_found_or_unauthorized"}

        # Begin execution row so the subscriber's UPDATE path has a target.
        execution_id = await scheduler_db.begin_execution(params.task_id)

        # Decode delivery_target: asyncpg returns JSONB as string.
        dt = task.get("delivery_target")
        if isinstance(dt, str):
            try:
                dt = json.loads(dt)
            except json.JSONDecodeError:
                dt = None

        try:
            await publish_fire(
                FireContext(
                    task_id=params.task_id,
                    execution_id=execution_id,
                    owner_user_id=task["user_id"],
                    kind=task.get("kind", "recurring"),
                    prompt=task.get("prompt"),
                    delivery_target=dt,
                    skill_ids=task.get("skill_ids"),
                    metadata=None,
                )
            )
        except Exception as exc:  # noqa: BLE001 — surface publish errors
            await scheduler_db.finish_execution(
                execution_id, "failed", error=f"publish: {exc}"[:500]
            )
            return {
                "ok": False,
                "error": "publish_failed",
                "message": str(exc),
            }

        return {
            "ok": True,
            "task_id": params.task_id,
            "execution_id": execution_id,
            "status": "running",
        }


def _dtos(rows: list[dict]) -> list[dict]:
    """Normalise DB rows for JSON-friendly tool output."""
    out: list[dict] = []
    for row in rows:
        copy = dict(row)
        # asyncpg returns JSONB as strings — decode once for the caller.
        dt = copy.get("delivery_target")
        if isinstance(dt, str):
            try:
                copy["delivery_target"] = json.loads(dt)
            except json.JSONDecodeError:
                pass
        out.append(copy)
    return out
