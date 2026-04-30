"""Hindsight Memory Tools — Agent kann aktiv Memories suchen + speichern (exec-11).

Ergaenzt die automatischen Memory Nodes (recall/retain) mit expliziten Tools
die der Agent selbst aufrufen kann.

memory_search: "Was weiss ich ueber EUR/USD?"
memory_add: "Merke dir: User bevorzugt Swing-Trading"
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import TYPE_CHECKING

from pydantic import BaseModel

from agent.tools.base import TradingTool

logger = logging.getLogger(__name__)

_ALLOWED_SEARCH_FACT_TYPES = {"experience", "observation", "world"}
_ALLOWED_WRITE_FACT_TYPES = {"experience", "observation"}
_MEMORY_ADD_DEDUPE_LOCK = asyncio.Lock()
_MEMORY_ADD_PENDING: dict[tuple[str, str, str, str], asyncio.Future[dict]] = {}
_MEMORY_ADD_RECENT: dict[tuple[str, str, str, str], tuple[float, dict]] = {}

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


def _normalize_memory_add_content(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


def _memory_add_dedupe_window_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("MEMORY_ADD_DEDUPE_WINDOW_SEC", "45")))
    except ValueError:
        return 45.0


async def _claim_memory_add_slot(
    key: tuple[str, str, str, str],
) -> tuple[str, asyncio.Future[dict] | dict | None]:
    window = _memory_add_dedupe_window_seconds()
    if window <= 0:
        return "disabled", None

    now = time.monotonic()
    async with _MEMORY_ADD_DEDUPE_LOCK:
        stale = [
            recent_key
            for recent_key, (seen_at, _result) in _MEMORY_ADD_RECENT.items()
            if now - seen_at > window
        ]
        for recent_key in stale:
            _MEMORY_ADD_RECENT.pop(recent_key, None)

        recent = _MEMORY_ADD_RECENT.get(key)
        if recent is not None:
            return "recent", recent[1]

        pending = _MEMORY_ADD_PENDING.get(key)
        if pending is not None:
            return "pending", pending

        future: asyncio.Future[dict] = asyncio.get_running_loop().create_future()
        _MEMORY_ADD_PENDING[key] = future
        return "owner", future


async def _finish_memory_add_slot(key: tuple[str, str, str, str], result: dict) -> None:
    window = _memory_add_dedupe_window_seconds()
    if window <= 0:
        return
    async with _MEMORY_ADD_DEDUPE_LOCK:
        pending = _MEMORY_ADD_PENDING.pop(key, None)
        if pending is not None and not pending.done():
            pending.set_result(result)
        if result.get("stored"):
            _MEMORY_ADD_RECENT[key] = (time.monotonic(), dict(result))


async def _recent_memory_add_matches(
    *,
    thread_id: str,
    bank_id: str,
    query: str,
    fact_type: str,
) -> list[dict]:
    window = _memory_add_dedupe_window_seconds()
    if window <= 0:
        return []
    normalized_query = _normalize_memory_add_content(query)
    if not normalized_query:
        return []

    now = time.monotonic()
    matches: list[dict] = []
    async with _MEMORY_ADD_DEDUPE_LOCK:
        stale = [
            recent_key
            for recent_key, (seen_at, _result) in _MEMORY_ADD_RECENT.items()
            if now - seen_at > window
        ]
        for recent_key in stale:
            _MEMORY_ADD_RECENT.pop(recent_key, None)

        for (recent_thread, recent_bank, recent_fact_type, normalized_content), (
            _seen_at,
            result,
        ) in _MEMORY_ADD_RECENT.items():
            if recent_thread != thread_id or recent_bank != bank_id:
                continue
            if fact_type and recent_fact_type != fact_type:
                continue
            query_terms = {term for term in normalized_query.split() if len(term) >= 8}
            content_terms = {term for term in normalized_content.split() if len(term) >= 8}
            has_overlap = bool(query_terms & content_terms)
            if (
                normalized_content not in normalized_query
                and normalized_query not in normalized_content
                and not has_overlap
            ):
                continue
            content = str(result.get("stored_content") or "").strip()
            if not content:
                continue
            matches.append(
                {
                    "text": content,
                    "type": recent_fact_type,
                    "entities": [],
                    "source": "recent_memory_add",
                }
            )
    return matches


async def _clear_memory_add_dedupe_for_tests() -> None:
    async with _MEMORY_ADD_DEDUPE_LOCK:
        _MEMORY_ADD_PENDING.clear()
        _MEMORY_ADD_RECENT.clear()


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
            engine_results = [
                {"text": f.text, "type": f.fact_type, "entities": f.entities or []}
                for f in result.results[:10]
            ]
            recent_results = await _recent_memory_add_matches(
                thread_id=str(ctx.thread_id),
                bank_id=bank_id,
                query=params.query,
                fact_type=fact_type,
            )
            seen_texts = {_normalize_memory_add_content(item["text"]) for item in engine_results}
            for item in recent_results:
                normalized_text = _normalize_memory_add_content(item["text"])
                if normalized_text and normalized_text not in seen_texts:
                    engine_results.append(item)
                    seen_texts.add(normalized_text)
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
                    "item_count": len(engine_results),
                    "engine_item_count": len(result.results),
                    "recent_item_count": len(recent_results),
                    "tool_name": self.name,
                    "source": "explicit_memory_tool",
                },
            )

            return {
                "results": engine_results,
                "count": len(engine_results),
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
                "must survive future conversations. Do not call this solely to implement "
                "automatic context-compaction safety; the pre-save archive pipeline handles "
                "that. Prefer this over save_memory for explicit long-term or evidence-bearing "
                "memory requests."
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
            dedupe_key = (
                str(ctx.thread_id),
                bank_id,
                effective_fact_type,
                _normalize_memory_add_content(params.content),
            )
            slot_kind, slot = await _claim_memory_add_slot(dedupe_key)
            if slot_kind in {"recent", "pending"}:
                prior = await slot if isinstance(slot, asyncio.Future) else slot
                facts_extracted = int((prior or {}).get("facts_extracted", 0) or 0)
                stored = bool((prior or {}).get("stored", False))
                await audit_log(
                    action=AuditAction.MEMORY_RETAIN,
                    thread_id=ctx.thread_id,
                    agent_id=ctx.user_id,
                    input_data=params.content[:2000],
                    success=stored,
                    metadata={
                        "bank_id": bank_id,
                        "route": "fusion",
                        "provider": "fusion",
                        "providers": "dedupe",
                        "storage_route": "dedupe",
                        "fact_type": effective_fact_type,
                        "original_fact_type": params.fact_type,
                        "item_count": 0,
                        "original_item_count": facts_extracted,
                        "tool_name": self.name,
                        "source": "explicit_memory_tool",
                        "deduplicated": True,
                        "dedupe_source": slot_kind,
                    },
                )
                return {
                    "stored": stored,
                    "facts_extracted": 0,
                    "deduplicated": True,
                    "original_facts_extracted": facts_extracted,
                }
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

            slot_result = {
                "stored": True,
                "facts_extracted": facts_extracted,
                "stored_content": params.content,
                "fact_type": effective_fact_type,
            }
            await _finish_memory_add_slot(dedupe_key, slot_result)
            return {
                "stored": True,
                "facts_extracted": facts_extracted,
            }
        except Exception as e:
            if "dedupe_key" in locals():
                await _finish_memory_add_slot(
                    dedupe_key,
                    {"stored": False, "facts_extracted": 0, "error": str(e)},
                )
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
