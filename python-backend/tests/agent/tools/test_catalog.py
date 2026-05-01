from __future__ import annotations

from typing import Any

from agent.tools.base import TradingTool
from agent.tools.catalog import (
    builtin_tool_catalog,
    catalog_entry_for_tool,
    search_tool_catalog,
    visible_tool_summaries,
)
from agent.tools.discovery import (
    expand_tool_definitions_from_results,
    selected_tools_for_turn,
    tool_names_from_search_results,
)
from agent.tools.registry import ToolRegistry
from agent.tools.tool_search import ToolSearchTool


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
    assert "tool_search" in by_name
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


def test_selected_tools_for_turn_defers_to_relevant_schemas_and_search_tool():
    tools = (
        ToolSearchTool(),
        _CatalogTool("memory_search", "Search memory."),
        _CatalogTool("sandbox_execute", "Execute code."),
        _CatalogTool("get_portfolio_summary", "Read portfolio."),
    )

    selected = selected_tools_for_turn(
        tools,
        "remember my portfolio memory",
        defer_schemas=True,
        limit=2,
        max_level=2,
    )

    assert [tool.name for tool in selected] == [
        "tool_search",
        "memory_search",
        "get_portfolio_summary",
    ]
    assert "sandbox_execute" not in {tool.name for tool in selected}


def test_selected_tools_for_turn_exact_name_can_load_high_risk_tool():
    tools = (
        ToolSearchTool(),
        _CatalogTool("memory_search", "Search memory."),
        _CatalogTool("sandbox_execute", "Execute code."),
    )

    selected = selected_tools_for_turn(
        tools,
        "use sandbox_execute for this code",
        defer_schemas=True,
        limit=2,
        max_level=2,
    )

    assert "sandbox_execute" in {tool.name for tool in selected}


def test_selected_tools_for_turn_suppresses_memory_writes_on_negative_memory_intent():
    tools = (
        ToolSearchTool(),
        _CatalogTool("memory_add", "Remember durable user memory with evidence."),
        _CatalogTool("save_memory", "Save a short-lived memory note."),
        _CatalogTool("retrieve_context", "Retrieve source grounded context."),
    )

    selected = selected_tools_for_turn(
        tools,
        "Use retrieve_context, but do not store this as personal memory.",
        defer_schemas=True,
        limit=3,
        max_level=2,
    )

    names = {tool.name for tool in selected}
    assert "retrieve_context" in names
    assert "tool_search" in names
    assert "memory_add" not in names
    assert "save_memory" not in names


def test_selected_tools_for_turn_suppresses_memory_tools_for_semantic_grounding():
    tools = (
        ToolSearchTool(),
        _CatalogTool("memory_add", "Remember durable user memory with evidence."),
        _CatalogTool("memory_search", "Search previous memory."),
        _CatalogTool("semantic_lookup", "Resolve semantic metric definitions."),
    )

    selected = selected_tools_for_turn(
        tools,
        "Use semantic_lookup to ground the term Sharpe ratio.",
        defer_schemas=True,
        limit=3,
        max_level=2,
    )

    names = {tool.name for tool in selected}
    assert "semantic_lookup" in names
    assert "tool_search" in names
    assert "memory_add" not in names
    assert "memory_search" not in names


def test_expand_tool_definitions_from_tool_search_results():
    tools = (
        ToolSearchTool(),
        _CatalogTool("memory_search", "Search memory."),
        _CatalogTool("get_portfolio_summary", "Read portfolio."),
    )
    current = [ToolSearchTool().definition()]
    results = [
        {
            "tool_call_id": "call-1",
            "tool_name": "tool_search",
            "result": {"tool_names": ["memory_search", "get_portfolio_summary"]},
            "error": None,
        }
    ]

    expanded = expand_tool_definitions_from_results(current, results, all_tools=tools)

    assert tool_names_from_search_results(results) == [
        "memory_search",
        "get_portfolio_summary",
    ]
    assert [item["name"] for item in expanded or []] == [
        "tool_search",
        "memory_search",
        "get_portfolio_summary",
    ]
