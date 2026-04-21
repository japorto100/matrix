"""Tests for RenderA2uiSurfaceTool — matches TradingTool ABC signature."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent.tools.a2ui_surface import RenderA2uiSurfaceTool


def _mock_ctx() -> MagicMock:
    """Stubbed AgentExecutionContext — the tool should not dereference it."""
    ctx = MagicMock()
    ctx.user_id = "test-user"
    ctx.session_id = "test-session"
    return ctx


@pytest.mark.asyncio
async def test_execute_returns_a2ui_envelope() -> None:
    tool = RenderA2uiSurfaceTool()
    tree = {"type": "Card", "children": [{"type": "Text", "text": "hello"}]}
    result = await tool.execute({"surface_id": "main", "tree": tree}, _mock_ctx())
    assert result == {"type": "a2ui", "surface_id": "main", "tree": tree}


@pytest.mark.asyncio
async def test_execute_rejects_none_tree() -> None:
    tool = RenderA2uiSurfaceTool()
    with pytest.raises(ValueError, match="tree"):
        await tool.execute({"surface_id": "main", "tree": None}, _mock_ctx())


@pytest.mark.asyncio
async def test_execute_rejects_empty_tree() -> None:
    tool = RenderA2uiSurfaceTool()
    with pytest.raises(ValueError, match="tree"):
        await tool.execute({"surface_id": "main", "tree": {}}, _mock_ctx())


@pytest.mark.asyncio
async def test_execute_rejects_missing_surface_id() -> None:
    tool = RenderA2uiSurfaceTool()
    with pytest.raises(ValueError, match="surface_id"):
        await tool.execute({"tree": {"type": "Card"}}, _mock_ctx())


def test_tool_name() -> None:
    assert RenderA2uiSurfaceTool().name == "render_a2ui_surface"


def test_tool_definition_shape() -> None:
    defn = RenderA2uiSurfaceTool().definition()
    assert defn["name"] == "render_a2ui_surface"
    assert "input_schema" in defn
    assert defn["input_schema"]["required"] == ["surface_id", "tree"]
