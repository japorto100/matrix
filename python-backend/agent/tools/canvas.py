"""Canvas Tools — exec-09 Phase 3

Agent kann Shapes auf dem tldraw Infinite Canvas erstellen, updaten und loeschen.
Die Tools senden Instruktionen zurueck die das Frontend interpretiert.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel

from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


class CreateShapeInput(BaseModel):
    shape_type: str  # "text" | "geo" | "arrow" | "note"
    text: str = ""
    x: float = 0
    y: float = 0
    width: float = 200
    height: float = 100


class UpdateShapeInput(BaseModel):
    shape_id: str
    text: str | None = None
    x: float | None = None
    y: float | None = None


class DeleteShapeInput(BaseModel):
    shape_id: str


class CreateCanvasShapeTool(TradingTool):
    """Creates a shape on the tldraw canvas."""

    input_model = CreateShapeInput

    @property
    def name(self) -> str:
        return "canvas_create_shape"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Creates a new shape on the infinite canvas. "
                "Types: text, geo (rectangle/ellipse), arrow, note. "
                "Returns the shape ID for later updates."
            ),
            "input_schema": CreateShapeInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        params = CreateShapeInput(**tool_input)
        shape_id = f"shape:{uuid.uuid4().hex[:8]}"
        return {
            "ok": True,
            "shape_id": shape_id,
            "action": "create",
            "shape_type": params.shape_type,
            "text": params.text,
            "x": params.x,
            "y": params.y,
            "width": params.width,
            "height": params.height,
        }


class UpdateCanvasShapeTool(TradingTool):
    """Updates an existing shape on the canvas."""

    input_model = UpdateShapeInput

    @property
    def name(self) -> str:
        return "canvas_update_shape"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": "Updates text or position of an existing canvas shape.",
            "input_schema": UpdateShapeInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        params = UpdateShapeInput(**tool_input)
        return {
            "ok": True,
            "action": "update",
            "shape_id": params.shape_id,
            "text": params.text,
            "x": params.x,
            "y": params.y,
        }


class CreateNovelBlockInput(BaseModel):
    text: str = ""
    x: float = 0
    y: float = 0
    width: float = 400
    height: float = 300


class CreateNovelBlockTool(TradingTool):
    """Creates an editable Novel (Notion-style) text block on the canvas."""

    input_model = CreateNovelBlockInput

    @property
    def name(self) -> str:
        return "canvas_create_novel_block"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": (
                "Creates an editable rich-text block (Notion-style) on the canvas. "
                "Users can edit the content inline with slash-commands, formatting, etc."
            ),
            "input_schema": CreateNovelBlockInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        params = CreateNovelBlockInput(**tool_input)
        shape_id = f"novel:{uuid.uuid4().hex[:8]}"
        return {
            "ok": True,
            "shape_id": shape_id,
            "action": "create",
            "shape_type": "novel",
            "text": params.text,
            "x": params.x,
            "y": params.y,
            "width": params.width,
            "height": params.height,
        }


class DeleteCanvasShapeTool(TradingTool):
    """Deletes a shape from the canvas."""

    input_model = DeleteShapeInput

    @property
    def name(self) -> str:
        return "canvas_delete_shape"

    def definition(self) -> dict:
        return {
            "name": self.name,
            "description": "Deletes a shape from the infinite canvas by its ID.",
            "input_schema": DeleteShapeInput.model_json_schema(),
        }

    async def execute(self, tool_input: dict, ctx: "AgentExecutionContext") -> dict:
        params = DeleteShapeInput(**tool_input)
        return {
            "ok": True,
            "action": "delete",
            "shape_id": params.shape_id,
        }
