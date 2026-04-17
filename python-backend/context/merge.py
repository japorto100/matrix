# Multi-Source Context Merge — Phase 10b.3
# Ref: CONTEXT_ENGINEERING.md Sek. 6
# Prompt-Block-Reihenfolge (System → Skills → Memory → History) siehe
# specs/execution/exec-context.md §5 — dieses Modul merged Retrieval-Fragmente, nicht den vollen Chat-Prompt.

from __future__ import annotations

from typing import Any

from context.policy import (
    BRIDGE_PERSONAL_KB_LAYER,
    BRIDGE_WORLD_LAYER,
    PERSONAL_DERIVED_LAYER,
    PERSONAL_RAW_LAYER,
    WORLD_KG_LAYER,
    apply_context_policy,
    normalize_context_layer,
)

# Max fragments per canonical layer.
MAX_WORLD_KG = 10
MAX_PERSONAL_DERIVED = 3
MAX_PERSONAL_RAW = 3
MAX_PERSONAL_KB = 2
MAX_WORLD_EVIDENCE = 5


def merge_fragments(
    fragments: list[dict[str, Any]],
    *,
    max_kg: int = MAX_WORLD_KG,
    max_episodic: int = MAX_PERSONAL_RAW,
    max_vector: int = MAX_WORLD_EVIDENCE,
    max_personal_derived: int = MAX_PERSONAL_DERIVED,
    max_personal_kb: int = MAX_PERSONAL_KB,
    min_relevance: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Merge fragments using the canonical context layer order.

    Compatibility:
    - `kg` -> `world_kg`
    - `episodic` -> `personal_raw`
    - `vector` -> `bridge_world`
    """
    by_layer: dict[str, list[dict[str, Any]]] = {
        WORLD_KG_LAYER: [],
        PERSONAL_DERIVED_LAYER: [],
        PERSONAL_RAW_LAYER: [],
        BRIDGE_PERSONAL_KB_LAYER: [],
        BRIDGE_WORLD_LAYER: [],
    }
    for f in fragments:
        rel = f.get("relevance", 0.5)
        if rel >= min_relevance:
            block = dict(f)
            block["sourceLayer"] = normalize_context_layer(block)
            by_layer.setdefault(block["sourceLayer"], []).append(block)

    merged: list[dict[str, Any]] = []
    layer_caps = {
        WORLD_KG_LAYER: max_kg,
        PERSONAL_DERIVED_LAYER: max_personal_derived,
        PERSONAL_RAW_LAYER: max_episodic,
        BRIDGE_PERSONAL_KB_LAYER: max_personal_kb,
        BRIDGE_WORLD_LAYER: max_vector,
    }
    for layer, items in by_layer.items():
        items.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        merged.extend(items[: layer_caps.get(layer, max_vector)])

    ordered, _, _ = apply_context_policy(merged, consumer="merge_layer")

    seen_symbols: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for item in ordered:
        symbols = item.get("metadata", {}).get("symbols", []) or item.get("symbols", [])
        key = ",".join(sorted(symbols)) if symbols else str(id(item))
        if key not in seen_symbols or not symbols:
            seen_symbols.add(key)
            deduped.append(item)

    return deduped
