"""Provider-agnostic tool discovery and deferred schema selection."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Any

from agent.tools.base import TradingTool
from agent.tools.catalog import builtin_tool_catalog, search_tool_catalog

TOOL_SEARCH_NAME = "tool_search"


def bool_env(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if raw in {"", "default"}:
        return default
    return raw in {"1", "true", "yes", "on"}


def int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


def tool_discovery_matches(
    tools: Iterable[TradingTool],
    query: str,
    *,
    limit: int = 5,
    max_level: int = 2,
    include_exact_names: bool = True,
) -> list[dict[str, Any]]:
    """Return ranked metadata-only tool matches for a query."""

    tool_list = list(tools)
    q = (query or "").strip()
    if not q or not tool_list:
        return []

    entries = builtin_tool_catalog(tool_list)
    matches = search_tool_catalog(
        entries,
        q,
        limit=limit,
        max_level=max_level,
    )
    by_name = {str(item.get("name") or ""): dict(item) for item in matches}
    if include_exact_names:
        for tool in tool_list:
            if tool.name == TOOL_SEARCH_NAME:
                continue
            if _query_mentions_tool(q, tool.name):
                entry = next((e for e in entries if e.name == tool.name), None)
                if entry is not None:
                    item = entry.as_dict()
                    item.pop("description_hash", None)
                    item.pop("input_schema_hash", None)
                    item["score"] = max(float(by_name.get(tool.name, {}).get("score", 0)), 99.0)
                    item["matched_terms"] = [tool.name]
                    by_name[tool.name] = item

    ranked = sorted(
        by_name.values(),
        key=lambda item: (
            -float(item.get("score", 0.0) or 0.0),
            str(item.get("name") or ""),
        ),
    )
    return ranked[: max(0, limit)]


def selected_tools_for_turn(
    tools: Iterable[TradingTool],
    query: str,
    *,
    defer_schemas: bool | None = None,
    limit: int | None = None,
    max_level: int | None = None,
) -> tuple[TradingTool, ...]:
    """Select the full schemas that should be exposed to the model this turn.

    Execution still happens through the full registry. This function only
    reduces the provider tool-definition payload and always keeps `tool_search`
    available as the fallback discovery primitive when present.
    """

    tool_list = tuple(tools)
    if not tool_list:
        return ()
    if defer_schemas is None:
        defer_schemas = _defer_tool_schemas_enabled(tool_list)
    if not defer_schemas:
        return tool_list

    q = (query or "").strip()
    configured_limit = max(1, limit or int_env("AGENT_TOOL_SCHEMA_DISCOVERY_LIMIT", 3))
    configured_max_level = max(1, max_level or int_env("AGENT_TOOL_SCHEMA_DISCOVERY_MAX_LEVEL", 2))
    selected_names: list[str] = []
    if q:
        selected_names.extend(
            str(item.get("name") or "")
            for item in tool_discovery_matches(
                tool_list,
                q,
                limit=configured_limit,
                max_level=configured_max_level,
            )
            if item.get("name")
        )

    if any(tool.name == TOOL_SEARCH_NAME for tool in tool_list):
        selected_names.append(TOOL_SEARCH_NAME)

    seen: set[str] = set()
    ordered = []
    for name in selected_names:
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)
    if not ordered:
        return tuple(tool for tool in tool_list if tool.name == TOOL_SEARCH_NAME)
    selected = tuple(tool for tool in tool_list if tool.name in set(ordered))
    return selected or tool_list


def expand_tool_definitions_from_results(
    current_definitions: list[dict[str, Any]] | None,
    tool_results: list[dict[str, Any]] | None,
    *,
    all_tools: Iterable[TradingTool],
) -> list[dict[str, Any]] | None:
    """Append schemas selected by `tool_search` results to current definitions."""

    names = tool_names_from_search_results(tool_results or [])
    if not names:
        return None
    existing = {
        str(defn.get("name") or "")
        for defn in (current_definitions or [])
        if isinstance(defn, dict)
    }
    by_name = {tool.name: tool for tool in all_tools}
    merged = list(current_definitions or [])
    for name in names:
        if name in existing or name not in by_name:
            continue
        merged.append(by_name[name].definition())
        existing.add(name)
    return merged


def tool_names_from_search_results(tool_results: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for result in tool_results:
        if result.get("tool_name") != TOOL_SEARCH_NAME:
            continue
        payload = result.get("result")
        if not isinstance(payload, dict):
            continue
        for item in payload.get("matches") or []:
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
        for name in payload.get("tool_names") or []:
            if name:
                names.append(str(name))
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        if name == TOOL_SEARCH_NAME or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _defer_tool_schemas_enabled(tools: tuple[TradingTool, ...]) -> bool:
    raw = os.environ.get("AGENT_DEFER_TOOL_SCHEMAS", "auto").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    threshold = max(1, int_env("AGENT_DEFER_TOOL_SCHEMA_THRESHOLD", 12))
    return len(tools) >= threshold


def _query_mentions_tool(query: str, tool_name: str) -> bool:
    normalized_query = query.lower()
    normalized_name = tool_name.lower()
    spaced = normalized_name.replace("_", " ")
    return bool(
        re.search(rf"(?<![a-z0-9_]){re.escape(normalized_name)}(?![a-z0-9_])", normalized_query)
        or re.search(rf"(?<![a-z0-9]){re.escape(spaced)}(?![a-z0-9])", normalized_query)
    )
