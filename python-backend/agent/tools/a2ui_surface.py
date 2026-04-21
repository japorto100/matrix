"""RenderA2uiSurfaceTool — virtual tool wrapping an A2UI widget-tree as tool-result.

Ansatz Y from the spec: reuses the existing tool-result SSE streaming path.
The agent emits this tool call, and the frontend `ToolOutputRenderer`
recognizes the `type="a2ui"` envelope and mounts `<A2UIRenderer>` inline.

Signature matches TradingTool ABC exactly: `execute(tool_input, ctx)`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent.tools.base import TradingTool

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


# Must mirror frontend/src/features/agent/lib/a2uiTreeSchema.ts ALLOWED_TYPES.
ALLOWED_A2UI_TYPES = (
    "Card",
    "Column",
    "Row",
    "List",
    "Text",
    "Image",
    "Icon",
    "Video",
    "AudioPlayer",
    "Button",
    "TextField",
    "CheckBox",
    "ChoicePicker",
    "Slider",
    "DateTimeInput",
    "Divider",
    "Modal",
    "Tabs",
    "Chart",
)


class RenderA2uiSurfaceTool(TradingTool):
    """Emit an A2UI widget-tree bound to a surface id."""

    @property
    def name(self) -> str:
        return "render_a2ui_surface"

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": (
                "Render a rich UI widget tree on the frontend. "
                "Use surface_id 'main' for the standalone dashboard canvas on '/'; "
                "use 'chat-<messageId>' for inline chat-message widgets. "
                "tree is an A2UI v0.9 component-tree JSON with allowed types: "
                + ", ".join(ALLOWED_A2UI_TYPES)
                + "."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "surface_id": {
                        "type": "string",
                        "description": (
                            "Surface identifier (e.g. 'main', 'chat-<id>')"
                        ),
                    },
                    "tree": {
                        "type": "object",
                        "description": "A2UI v0.9 component-tree JSON",
                    },
                },
                "required": ["surface_id", "tree"],
            },
        }

    async def execute(
        self, tool_input: dict[str, Any], ctx: AgentExecutionContext
    ) -> dict[str, Any]:
        surface_id = tool_input.get("surface_id")
        tree = tool_input.get("tree")
        if not surface_id or not isinstance(surface_id, str):
            raise ValueError("surface_id required (non-empty string)")
        if not tree or not isinstance(tree, dict):
            raise ValueError("tree must be a non-empty dict")
        return {"type": "a2ui", "surface_id": surface_id, "tree": tree}
