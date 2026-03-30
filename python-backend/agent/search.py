# Agentic Search — Phase 10d
# Codebase Search, News Search (Emergent Mind/arXiv), Memory Search
# Ref: AGENT_TOOLS.md Sek. 6

from __future__ import annotations

from typing import Any

from agent.memory_client import get_episodes, post_vector_search

# Allowlist for codebase search (scope-begrenzt)
CODEBASE_ALLOWLIST = [
    "docs/",
    "python-backend/python-agent/",
    "python-backend/python-compute/",
    "python-backend/services/",
]


async def memory_search(query: str, *, episodic_limit: int = 5, vector_limit: int = 5) -> dict[str, Any]:
    """Episodic + Semantic (Vector) search. Phase 10d.3."""
    episodic: list[dict[str, Any]] = []
    vector: list[dict[str, Any]] = []
    try:
        ep_data = await get_episodes(limit=episodic_limit)
        if ep_data.get("ok") and ep_data.get("episodes"):
            episodic = ep_data["episodes"][:episodic_limit]
    except Exception:
        pass
    try:
        vec_data = await post_vector_search(query, n_results=vector_limit)
        if vec_data.get("ok") and vec_data.get("results"):
            vector = vec_data["results"]
    except Exception:
        pass
    return {"episodic": episodic, "vector": vector, "query": query}


async def codebase_search(query: str, *, allowlist: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Codebase search with allowlist. Phase 10d.1.
    Scope-begrenzt: only paths in allowlist. Stub returns empty; implement with ripgrep/glob.
    """
    allowlist = allowlist or CODEBASE_ALLOWLIST
    # Stub: would run rg/glob over allowlist paths, return matches
    return []


async def news_search(query: str, *, source: str = "emergent_mind") -> list[dict[str, Any]]:
    """
    News/Research search. Phase 10d.2.
    Evaluated: Emergent Mind API, arXiv API. Stub for now.
    """
    # Stub: would call Emergent Mind or arXiv API
    return []
