# Context Assembler — Phase 10a.4
# Assembles context from Memory layers (KG, Episodic, Vector) for agent roles
# Ref: CONTEXT_ENGINEERING.md Sek. 3-4, MEMORY_ARCHITECTURE.md

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from agent.memory_client import (
    get_episodes,
    get_kg_nodes,
    post_vector_search,
)


@dataclass
class ContextFragment:
    """Single context fragment with relevance metadata."""

    source: str  # "kg" | "episodic" | "vector"
    content: str | dict[str, Any]
    relevance: float
    timestamp: str | None = None
    metadata: dict[str, Any] | None = None


def _compute_freshness(timestamp_str: str | None, max_age_hours: float = 168) -> float:
    """Freshness score 0-1. CE Sek. 4.1."""
    if not timestamp_str:
        return 0.5
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_hours = (now - ts).total_seconds() / 3600
        if age_hours < 2:
            return 1.0
        if age_hours < 24:
            return 0.7
        if age_hours < 168:  # 7d
            return 0.3
        return max(0.1, 1.0 - (age_hours / max_age_hours))
    except Exception:
        return 0.5


def _relevance_score(
    fragment: ContextFragment,
    query: str,
    user_symbols: list[str] | None = None,
) -> float:
    """4-dimension relevance per CE Sek. 4."""
    freshness = _compute_freshness(fragment.timestamp)
    proximity = 0.5  # Placeholder: would use user_symbols vs fragment content
    confidence = fragment.metadata.get("confidence", 0.7) if fragment.metadata else 0.7
    regime_fit = 0.6  # Placeholder: would use current regime
    return 0.30 * freshness + 0.25 * proximity + 0.25 * confidence + 0.20 * regime_fit


async def assemble_context(
    query: str,
    *,
    kg_node_type: str = "Stratagem",
    kg_limit: int = 10,
    episodic_limit: int = 3,
    vector_limit: int = 5,
    min_relevance: float = 0.3,
    user_symbols: list[str] | None = None,
) -> tuple[list[ContextFragment], list[str]]:
    """
    Assemble context from Memory layers for agent.
    Returns (fragments, flags). Flags indicate degraded layers (e.g. "NO_KG_CONTEXT").
    """
    fragments: list[ContextFragment] = []
    flags: list[str] = []

    # 1. KG Backend (M2a)
    try:
        data = await get_kg_nodes(node_type=kg_node_type, limit=kg_limit)
        if data.get("ok") and data.get("nodes"):
            for i, node in enumerate(data["nodes"][:kg_limit]):
                frag = ContextFragment(
                    source="kg",
                    content=node,
                    relevance=0.8 - (i * 0.05),
                    metadata={"nodeType": kg_node_type},
                )
                frag = ContextFragment(
                    source=frag.source,
                    content=frag.content,
                    relevance=_relevance_score(frag, query, user_symbols),
                    timestamp=frag.timestamp,
                    metadata=frag.metadata,
                )
                if frag.relevance >= min_relevance:
                    fragments.append(frag)
        else:
            flags.append("NO_KG_CONTEXT")
    except Exception:
        flags.append("NO_KG_CONTEXT")

    # 2. Episodic (M3)
    try:
        data = await get_episodes(limit=episodic_limit)
        if data.get("ok") and data.get("episodes"):
            for ep in data["episodes"][:episodic_limit]:
                frag = ContextFragment(
                    source="episodic",
                    content=ep,
                    relevance=0.6,
                    timestamp=ep.get("created_at"),
                    metadata={"agent_role": ep.get("agent_role", "")},
                )
                frag = ContextFragment(
                    source=frag.source,
                    content=frag.content,
                    relevance=_relevance_score(frag, query, user_symbols),
                    timestamp=frag.timestamp,
                    metadata=frag.metadata,
                )
                if frag.relevance >= min_relevance:
                    fragments.append(frag)
    except Exception:
        flags.append("NO_EPISODIC_CONTEXT")

    # 3. Vector (M4)
    try:
        data = await post_vector_search(query, n_results=vector_limit)
        if data.get("ok") and data.get("results"):
            for r in data["results"]:
                frag = ContextFragment(
                    source="vector",
                    content={"text": r.get("text", ""), "distance": r.get("distance", 0)},
                    relevance=0.9 - (r.get("distance", 0) * 0.2),
                    metadata=r.get("metadata", {}),
                )
                if frag.relevance >= min_relevance:
                    fragments.append(frag)
        else:
            flags.append("NO_VECTOR_CONTEXT")
    except Exception:
        flags.append("NO_VECTOR_CONTEXT")

    # Sort by relevance descending
    fragments.sort(key=lambda f: f.relevance, reverse=True)
    return fragments, flags
