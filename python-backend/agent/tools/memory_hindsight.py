"""Hindsight Memory Tools — Agent kann aktiv Memories suchen + speichern (exec-11).

Ergaenzt die automatischen Memory Nodes (recall/retain) mit expliziten Tools
die der Agent selbst aufrufen kann.

memory_search: "Was weiss ich ueber EUR/USD?"
memory_add: "Merke dir: User bevorzugt Swing-Trading"
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel

from agent.tools.base import TradingTool

logger = logging.getLogger(__name__)

_ALLOWED_SEARCH_FACT_TYPES = {"experience", "observation", "world"}
_ALLOWED_WRITE_FACT_TYPES = {"experience", "observation"}

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class MemorySearchInput(BaseModel):
    query: str
    fact_type: str = ""  # empty = all; experience/user/world when explicitly needed


class MemoryAddInput(BaseModel):
    content: str
    fact_type: str = "experience"


def _normalize_search_fact_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in _ALLOWED_SEARCH_FACT_TYPES else ""


def _normalize_write_fact_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _ALLOWED_WRITE_FACT_TYPES:
        return normalized
    return "experience"


async def _submit_summary_retain_background(
    *,
    engine,
    bank_id: str,
    contents: list[dict],
) -> None:
    submit_async = getattr(engine, "submit_async_retain", None)
    if not callable(submit_async):
        return
    try:
        from hindsight_api.models import RequestContext

        await submit_async(
            bank_id=bank_id,
            contents=contents,
            request_context=RequestContext(),
            route="summary",
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("background memory summary retain failed: %s", exc)


class MemorySearchTool(TradingTool):
    """Search agent memory for relevant facts."""

    input_model = MemorySearchInput

    @property
    def name(self) -> str:
        return "memory_search"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Search your long-term memory for relevant facts, experiences, and knowledge. "
                "Use this when the user explicitly says to use memory_search, asks you to recall "
                "stored knowledge, or you need past preferences, decisions, project memories, "
                "or exact evidence before answering. "
                "Returns the most relevant memories ranked by relevance."
            ),
            "input_schema": MemorySearchInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: AgentExecutionContext) -> dict:
        from agent.audit.logger import AuditAction, audit_log
        from memory_fusion.engine import get_bank_id, get_memory_engine

        engine = await get_memory_engine()
        if engine is None:
            return {"results": [], "message": "Memory not available"}

        try:
            from hindsight_api.engine.memory_engine import Budget
            from hindsight_api.models import RequestContext

            params = MemorySearchInput(**tool_input)
            bank_id = get_bank_id(ctx.user_id)
            fact_type = _normalize_search_fact_type(params.fact_type)
            fact_filter = [fact_type] if fact_type else None

            result = await engine.recall_async(
                bank_id=bank_id,
                query=params.query,
                fact_type=fact_filter,
                budget=Budget.MID,
                max_tokens=2000,
                request_context=RequestContext(),
            )
            await audit_log(
                action=AuditAction.MEMORY_RECALL,
                thread_id=ctx.thread_id,
                agent_id=ctx.user_id,
                success=True,
                metadata={
                    "bank_id": bank_id,
                    "route": "fusion",
                    "provider": "fusion",
                    "providers": "fusion",
                    "query": params.query[:300],
                    "fact_type": fact_type,
                    "original_fact_type": params.fact_type,
                    "item_count": len(result.results),
                    "tool_name": self.name,
                    "source": "explicit_memory_tool",
                },
            )

            return {
                "results": [
                    {"text": f.text, "type": f.fact_type, "entities": f.entities or []}
                    for f in result.results[:10]
                ],
                "count": len(result.results),
            }
        except Exception as e:
            await audit_log(
                action=AuditAction.MEMORY_RECALL,
                thread_id=ctx.thread_id,
                agent_id=ctx.user_id,
                success=False,
                metadata={
                    "route": "fusion",
                    "provider": "fusion",
                    "providers": "fusion",
                    "tool_name": self.name,
                    "source": "explicit_memory_tool",
                    "error": str(e)[:500],
                },
            )
            return {"results": [], "error": str(e)}


class MemoryAddTool(TradingTool):
    """Explicitly store a fact in agent memory."""

    input_model = MemoryAddInput

    @property
    def name(self) -> str:
        return "memory_add"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Store an important fact, preference, decision, project memory, or exact "
                "evidence in persistent long-term memory. Use this when the user explicitly "
                "says to use memory_add, asks you to remember something, or when information "
                "must survive context compaction and future conversations. Prefer this over "
                "save_memory for anything long-term or evidence-bearing."
            ),
            "input_schema": MemoryAddInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: AgentExecutionContext) -> dict:
        from agent.audit.logger import AuditAction, audit_log
        from memory_fusion.engine import get_bank_id, get_memory_engine

        engine = await get_memory_engine()
        if engine is None:
            return {"stored": False, "message": "Memory not available"}

        try:
            from hindsight_api.models import RequestContext

            params = MemoryAddInput(**tool_input)
            bank_id = get_bank_id(ctx.user_id)

            # Tag mit Agent-Klasse fuer Memory Sharing Sichtbarkeit
            role_tag = getattr(ctx, "agent_class", "advisory")
            effective_fact_type = _normalize_write_fact_type(params.fact_type)
            content_items = [
                {
                    "content": params.content,
                    "context": f"Explicitly stored by agent (thread:{ctx.thread_id})",
                    "tags": [role_tag],
                    "fact_type": effective_fact_type,
                    "metadata": {"original_fact_type": params.fact_type},
                }
            ]
            try:
                unit_ids = await engine.retain_batch_async(
                    bank_id=bank_id,
                    contents=content_items,
                    request_context=RequestContext(),
                    route="verbatim",
                )
                storage_route = "fusion"
                storage_providers = "verbatim,summary_async"
            except TypeError:
                unit_ids = await engine.retain_batch_async(
                    bank_id=bank_id,
                    contents=content_items,
                    request_context=RequestContext(),
                )
                storage_route = "fusion"
                storage_providers = "fusion"

            summary_status = "background_queued"
            try:
                asyncio.create_task(
                    _submit_summary_retain_background(
                        engine=engine,
                        bank_id=bank_id,
                        contents=content_items,
                    )
                )
            except Exception:
                summary_status = "background_dispatch_failed"

            facts_extracted = sum(len(ids) for ids in unit_ids)
            await audit_log(
                action=AuditAction.MEMORY_RETAIN,
                thread_id=ctx.thread_id,
                agent_id=ctx.user_id,
                input_data=params.content[:2000],
                success=True,
                metadata={
                    "bank_id": bank_id,
                    "route": storage_route,
                    "provider": "fusion",
                    "providers": storage_providers,
                    "storage_route": "verbatim" if storage_providers != "fusion" else "fusion",
                    "fact_type": effective_fact_type,
                    "original_fact_type": params.fact_type,
                    "item_count": facts_extracted,
                    "tool_name": self.name,
                    "source": "explicit_memory_tool",
                    "summary_status": summary_status,
                },
            )

            return {
                "stored": True,
                "facts_extracted": facts_extracted,
            }
        except Exception as e:
            await audit_log(
                action=AuditAction.MEMORY_RETAIN,
                thread_id=ctx.thread_id,
                agent_id=ctx.user_id,
                success=False,
                metadata={
                    "route": "fusion",
                    "provider": "fusion",
                    "providers": "fusion",
                    "tool_name": self.name,
                    "source": "explicit_memory_tool",
                    "error": str(e)[:500],
                },
            )
            return {"stored": False, "error": str(e)}
