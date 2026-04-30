from __future__ import annotations

from typing import Any

from agent.tools.base import TradingTool
from agent.tools.catalog import (
    builtin_tool_catalog,
    catalog_entry_for_tool,
    search_tool_catalog,
    visible_tool_summaries,
)
from agent.tools.registry import ToolRegistry


class _CatalogTool(TradingTool):
    def __init__(self, name: str, description: str) -> None:
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    def definition(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},
        }

    async def execute(self, tool_input: dict[str, Any], ctx: Any) -> dict[str, Any]:
        return {"ok": True}


def test_catalog_entry_classifies_normal_builtin_tools():
    entry = catalog_entry_for_tool(
        _CatalogTool("memory_add", "Remember durable user memory with evidence.")
    )

    assert entry.source == "builtin"
    assert entry.group == "memory"
    assert entry.risk == "medium"
    assert entry.approval == "confirm"
    assert "memory-access" in entry.policy_reasons
    assert len(entry.description_hash) == 64
    assert len(entry.input_schema_hash) == 64


def test_catalog_entry_marks_code_execution_as_confirm_level():
    entry = catalog_entry_for_tool(
        _CatalogTool("sandbox_execute", "Execute Python code in a sandbox.")
    )

    assert entry.group == "code_execution"
    assert entry.risk == "critical"
    assert entry.approval == "confirm"
    assert entry.progressive_disclosure_level == 3


def test_builtin_catalog_covers_real_registry_tools():
    catalog = builtin_tool_catalog(ToolRegistry.load().all())
    by_name = {entry.name: entry for entry in catalog}

    assert "memory_add" in by_name
    assert "semantic_lookup" in by_name
    assert "retrieve_context" in by_name
    assert "sandbox_execute" in by_name
    assert "get_portfolio_summary" in by_name
    assert by_name["semantic_lookup"].group == "semantic"
    assert by_name["retrieve_context"].group == "retrieval"
    assert by_name["sandbox_execute"].risk == "critical"
    assert by_name["get_portfolio_summary"].progressive_disclosure_level == 1


def test_visible_tool_summaries_apply_group_tool_and_level_filters():
    entries = [
        catalog_entry_for_tool(_CatalogTool("memory_search", "Search memory.")),
        catalog_entry_for_tool(_CatalogTool("sandbox_execute", "Execute code.")),
        catalog_entry_for_tool(_CatalogTool("get_portfolio_summary", "Read portfolio.")),
    ]

    visible = visible_tool_summaries(
        entries,
        allowed_groups={"memory", "market"},
        max_level=2,
    )

    assert [item["name"] for item in visible] == ["memory_search", "get_portfolio_summary"]
    assert all(set(item) == {"name", "group", "summary", "risk", "approval"} for item in visible)


def test_search_tool_catalog_returns_progressively_disclosed_matches():
    entries = [
        catalog_entry_for_tool(_CatalogTool("memory_search", "Search memory.")),
        catalog_entry_for_tool(_CatalogTool("sandbox_execute", "Execute code.")),
        catalog_entry_for_tool(_CatalogTool("get_portfolio_summary", "Read portfolio.")),
    ]

    matches = search_tool_catalog(entries, "remember portfolio memory", max_level=2)

    assert [item["name"] for item in matches] == [
        "memory_search",
        "get_portfolio_summary",
    ]
    assert matches[0]["matched_terms"]
    assert "input_schema" not in matches[0]
