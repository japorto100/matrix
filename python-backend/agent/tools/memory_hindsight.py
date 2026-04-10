"""Hindsight Memory Tools — Agent kann aktiv Memories suchen + speichern (exec-11).

Ergaenzt die automatischen Memory Nodes (recall/retain) mit expliziten Tools
die der Agent selbst aufrufen kann.

memory_search: "Was weiss ich ueber EUR/USD?"
memory_add: "Merke dir: User bevorzugt Swing-Trading"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class MemorySearchInput(BaseModel):
    query: str
    fact_type: str = "world"  # world | experience


class MemoryAddInput(BaseModel):
    content: str
    fact_type: str = "world"


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
                "Use this when you need to recall information from past conversations or stored knowledge. "
                "Returns the most relevant memories ranked by relevance."
            ),
            "input_schema": MemorySearchInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: AgentExecutionContext) -> dict:
        from agent.memory.engine import get_bank_id, get_memory_engine

        engine = await get_memory_engine()
        if engine is None:
            return {"results": [], "message": "Memory not available"}

        try:
            from hindsight_api.engine.memory_engine import Budget
            from hindsight_api.models import RequestContext

            params = MemorySearchInput(**tool_input)
            bank_id = get_bank_id(ctx.user_id)

            result = await engine.recall_async(
                bank_id=bank_id,
                query=params.query,
                fact_type=[params.fact_type],
                budget=Budget.MID,
                max_tokens=2000,
                request_context=RequestContext(),
            )

            return {
                "results": [
                    {"text": f.text, "type": f.fact_type, "entities": f.entities or []}
                    for f in result.results[:10]
                ],
                "count": len(result.results),
            }
        except Exception as e:
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
                "Store an important fact, preference, or learning in your long-term memory. "
                "Use this when the user tells you something important to remember, "
                "or when you discover something worth keeping for future conversations."
            ),
            "input_schema": MemoryAddInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: AgentExecutionContext) -> dict:
        from agent.memory.engine import get_bank_id, get_memory_engine

        engine = await get_memory_engine()
        if engine is None:
            return {"stored": False, "message": "Memory not available"}

        try:
            from hindsight_api.models import RequestContext

            params = MemoryAddInput(**tool_input)
            bank_id = get_bank_id(ctx.user_id)

            # Tag mit Agent-Klasse fuer Memory Sharing Sichtbarkeit
            role_tag = getattr(ctx, "agent_class", "advisory")
            unit_ids = await engine.retain_batch_async(
                bank_id=bank_id,
                contents=[{
                    "content": params.content,
                    "context": f"Explicitly stored by agent (thread:{ctx.thread_id})",
                    "tags": [role_tag],
                }],
                request_context=RequestContext(),
            )

            return {
                "stored": True,
                "facts_extracted": sum(len(ids) for ids in unit_ids),
            }
        except Exception as e:
            return {"stored": False, "error": str(e)}
