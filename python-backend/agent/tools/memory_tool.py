# Memory tools — Phase 22g / AMC1 (save/load working memory)
# Phase 22g+: ABP.2b — Pydantic input models replace manual dict validation.
# Allows agent to persist and retrieve reasoning scratchpad across turns.

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class SaveMemoryInput(BaseModel):
    key: str = Field(min_length=1, description="Short identifier for this memory entry")
    content: str = Field(min_length=1, description="The content to save")


class LoadMemoryInput(BaseModel):
    key: str = Field(min_length=1, description="The key used when saving the memory entry")


class SaveMemoryTool(TradingTool):
    """Save a note to agent working memory (M5 scratchpad) for later retrieval."""

    input_model = SaveMemoryInput

    @property
    def name(self) -> str:
        return "save_memory"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Save a note or piece of information to working memory so it can be "
                "retrieved later in the same session or future sessions. "
                "Use this to remember key insights, market observations, or analysis results."
            ),
            "input_schema": SaveMemoryInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        from agent.working_memory import working_memory_set
        params = SaveMemoryInput(**tool_input)
        await working_memory_set(ctx.thread_id, params.key, params.content)
        return {"ok": True, "key": params.key, "saved": True}


class LoadMemoryTool(TradingTool):
    """Load a previously saved note from working memory by key."""

    input_model = LoadMemoryInput

    @property
    def name(self) -> str:
        return "load_memory"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Load a previously saved note from working memory by key. "
                "Returns the content if found, or null if the key does not exist."
            ),
            "input_schema": LoadMemoryInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        from agent.working_memory import working_memory_get
        params = LoadMemoryInput(**tool_input)
        data = await working_memory_get(ctx.thread_id)
        content = data.get(params.key)
        return {"ok": True, "key": params.key, "content": content, "found": content is not None}
