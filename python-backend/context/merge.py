# Multi-Source Context Merge — Phase 10b.3
# Simple merge: priority order, dedup by symbol, diversity floor
# Ref: CONTEXT_ENGINEERING.md Sek. 6
# Note: DyCP/LLMLingua-2 evaluated; simple merge chosen for MVP

from __future__ import annotations

from typing import Any

# Max fragments per layer (CE Sek. 4.3)
MAX_KG = 10
MAX_EPISODIC = 3
MAX_VECTOR = 5

# Diversity floor (CE Sek. 4.3)
MIN_REGIONS = 3
MIN_STRATAGEM_TYPES = 2


def merge_fragments(
    fragments: list[dict[str, Any]],
    *,
    max_kg: int = MAX_KG,
    max_episodic: int = MAX_EPISODIC,
    max_vector: int = MAX_VECTOR,
    min_relevance: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Merge fragments from multiple sources with caps and dedup.
    Priority: KG > Episodic > Vector (structured first).
    """
    by_source: dict[str, list[dict[str, Any]]] = {"kg": [], "episodic": [], "vector": []}
    for f in fragments:
        src = f.get("source", "vector")
        if src not in by_source:
            by_source[src] = []
        rel = f.get("relevance", 0.5)
        if rel >= min_relevance:
            by_source[src].append(f)

    # Sort each by relevance desc
    for src in by_source:
        by_source[src].sort(key=lambda x: x.get("relevance", 0), reverse=True)

    # Apply caps
    merged: list[dict[str, Any]] = []
    merged.extend(by_source["kg"][:max_kg])
    merged.extend(by_source["episodic"][:max_episodic])
    merged.extend(by_source["vector"][:max_vector])

    # Dedup by symbol (prefer KG over vector for same symbol)
    seen_symbols: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for f in merged:
        symbols = f.get("metadata", {}).get("symbols", []) or f.get("symbols", [])
        key = ",".join(sorted(symbols)) if symbols else str(id(f))
        if key not in seen_symbols or not symbols:
            seen_symbols.add(key)
            deduped.append(f)

    return deduped
