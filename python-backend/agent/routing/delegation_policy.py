"""Route/delegation metadata policy for the Matrix agent harness.

The current product scope keeps real subagents disabled. This module still
centralizes the schema so Meta-Harness can assert why a turn stayed direct,
used retrieval/tools, or deferred future delegation.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

MEMORY_TOOL_NAMES = frozenset({"memory_search", "memory_add", "save_memory", "load_memory"})
RETRIEVAL_TOOL_NAMES = frozenset(
    {"memory_search", "kg_search", "retrieve_context", "semantic_lookup"}
)


def _clean_tool_names(tool_names: Iterable[str]) -> list[str]:
    return [name for name in (str(value).strip() for value in tool_names) if name]


def route_taxonomy_for_tools(tool_names: Iterable[str]) -> str:
    """Map observed tool calls onto the stable Feature 020 route taxonomy."""

    names = set(_clean_tool_names(tool_names))
    if not names:
        return "direct_answer"
    if names & RETRIEVAL_TOOL_NAMES:
        return "retrieval_answer"
    return "tool_use"


def build_route_decision_metadata(
    *,
    runner: str,
    tool_names: Iterable[str],
    routing_reason: str = "not_evaluated",
    routing_used: bool = False,
    routing_picked_model: str = "",
    max_spawn_depth: int = 0,
    memory_scope: str = "current_user",
    allowed_tools: Iterable[str] | None = None,
    budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build non-secret audit metadata for one route/delegation decision."""

    names = _clean_tool_names(tool_names)
    route_taxonomy = route_taxonomy_for_tools(names)
    decision = "tool_use" if names else "direct_answer"
    allowed = _clean_tool_names(allowed_tools or names)
    return {
        "runner": runner or "unknown",
        "decision": decision,
        "route_taxonomy": route_taxonomy,
        "delegation_decision": "none",
        "delegate_kind": None,
        "spawn_depth": 0,
        "max_spawn_depth": max(0, int(max_spawn_depth)),
        "allowed_tools": allowed,
        "memory_scope": memory_scope,
        "budget": dict(budget or {}),
        "fallback_reason": "subagents_disabled",
        "tool_calls_count": len(names),
        "tool_names": names,
        "routing_reason": routing_reason,
        "routing_used": bool(routing_used),
        "routing_picked_model": routing_picked_model,
        "memory_route_requested": bool(set(names) & MEMORY_TOOL_NAMES),
        "retrieval_route_requested": bool(set(names) & RETRIEVAL_TOOL_NAMES),
    }
