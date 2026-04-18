"""Canonical context policy helpers for runtime, merge, and inspectors."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

from memory_fusion.semantics import (
    BRIDGE_PERSONAL_KB_LAYER,
    BRIDGE_WORLD_LAYER,
    DERIVED_ARTIFACT_TYPES,
    KB_ARTIFACT_TYPES,
    PERSONAL_DERIVED_LAYER,
    PERSONAL_RAW_LAYER,
    RAW_ARTIFACT_TYPES,
    WORLD_ARTIFACT_TYPES,
)

WORKING_MEMORY_LAYER = "working_memory"
WORLD_KG_LAYER = "world_kg"

ContextConsumer = Literal["llm_agent", "frontend_ui", "signal_pipeline", "merge_layer"]

ALL_CONTEXT_LAYERS = (
    WORKING_MEMORY_LAYER,
    WORLD_KG_LAYER,
    PERSONAL_DERIVED_LAYER,
    PERSONAL_RAW_LAYER,
    BRIDGE_PERSONAL_KB_LAYER,
    BRIDGE_WORLD_LAYER,
)

LEGACY_SOURCE_LAYER_MAP = {
    "kg": WORLD_KG_LAYER,
    "episodic": PERSONAL_RAW_LAYER,
    "vector": BRIDGE_WORLD_LAYER,
}

LAYER_ALIASES = {
    WORKING_MEMORY_LAYER: WORKING_MEMORY_LAYER,
    "working": WORKING_MEMORY_LAYER,
    "hot_cache": WORKING_MEMORY_LAYER,
    "hot-cache": WORKING_MEMORY_LAYER,
    WORLD_KG_LAYER: WORLD_KG_LAYER,
    "global_world_kg": WORLD_KG_LAYER,
    "global-world-kg": WORLD_KG_LAYER,
    PERSONAL_DERIVED_LAYER: PERSONAL_DERIVED_LAYER,
    "personal-derived": PERSONAL_DERIVED_LAYER,
    PERSONAL_RAW_LAYER: PERSONAL_RAW_LAYER,
    "personal-raw": PERSONAL_RAW_LAYER,
    BRIDGE_PERSONAL_KB_LAYER: BRIDGE_PERSONAL_KB_LAYER,
    "personal_kb": BRIDGE_PERSONAL_KB_LAYER,
    "personal-kb": BRIDGE_PERSONAL_KB_LAYER,
    "kb": BRIDGE_PERSONAL_KB_LAYER,
    BRIDGE_WORLD_LAYER: BRIDGE_WORLD_LAYER,
    "bridge-world": BRIDGE_WORLD_LAYER,
    "world": BRIDGE_WORLD_LAYER,
    "world_evidence": BRIDGE_WORLD_LAYER,
}

LAYER_LABELS = {
    WORKING_MEMORY_LAYER: "Working Memory",
    WORLD_KG_LAYER: "World KG",
    PERSONAL_DERIVED_LAYER: "Personal Derived Memory",
    PERSONAL_RAW_LAYER: "Personal Raw Evidence",
    BRIDGE_PERSONAL_KB_LAYER: "Personal Knowledgebase",
    BRIDGE_WORLD_LAYER: "World Evidence",
}

CONTEXT_TIER_LABELS = ("L0", "L1", "L2", "L3")


@dataclass(frozen=True)
class ContextPolicy:
    consumer: ContextConsumer
    layer_order: tuple[str, ...]
    allowed_layers: frozenset[str]
    recall_fact_types: tuple[str, ...]
    require_world_status: bool = True
    require_world_provenance: bool = True
    require_grounded_derived: bool = True


CONTEXT_POLICIES: dict[ContextConsumer, ContextPolicy] = {
    "llm_agent": ContextPolicy(
        consumer="llm_agent",
        layer_order=ALL_CONTEXT_LAYERS,
        allowed_layers=frozenset(ALL_CONTEXT_LAYERS),
        recall_fact_types=("world", "opinion", "observation", "experience"),
    ),
    "frontend_ui": ContextPolicy(
        consumer="frontend_ui",
        layer_order=ALL_CONTEXT_LAYERS,
        allowed_layers=frozenset(ALL_CONTEXT_LAYERS),
        recall_fact_types=("world", "opinion", "observation", "experience"),
        require_grounded_derived=False,
    ),
    "signal_pipeline": ContextPolicy(
        consumer="signal_pipeline",
        layer_order=(
            WORLD_KG_LAYER,
            BRIDGE_WORLD_LAYER,
            PERSONAL_DERIVED_LAYER,
            PERSONAL_RAW_LAYER,
        ),
        allowed_layers=frozenset(
            {
                WORLD_KG_LAYER,
                BRIDGE_WORLD_LAYER,
                PERSONAL_DERIVED_LAYER,
                PERSONAL_RAW_LAYER,
            }
        ),
        recall_fact_types=("world", "opinion", "observation", "experience"),
    ),
    "merge_layer": ContextPolicy(
        consumer="merge_layer",
        layer_order=ALL_CONTEXT_LAYERS,
        allowed_layers=frozenset(ALL_CONTEXT_LAYERS),
        recall_fact_types=("world", "opinion", "observation", "experience"),
    ),
}


def get_context_policy(consumer: ContextConsumer = "llm_agent") -> ContextPolicy:
    return CONTEXT_POLICIES[consumer]


def normalize_context_layer(item: dict[str, Any] | None) -> str:
    item = dict(item or {})
    metadata = item.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}

    explicit_candidates = (
        item.get("sourceLayer"),
        item.get("source_layer"),
        item.get("memory_layer"),
        metadata.get("sourceLayer"),
        metadata.get("source_layer"),
        metadata.get("memory_layer"),
    )
    for candidate in explicit_candidates:
        alias = LAYER_ALIASES.get(str(candidate or "").strip().lower())
        if alias:
            return alias

    legacy_source = str(item.get("source") or metadata.get("source") or "").strip().lower()
    if legacy_source in LEGACY_SOURCE_LAYER_MAP:
        return LEGACY_SOURCE_LAYER_MAP[legacy_source]

    artifact_type = str(
        item.get("artifactType")
        or item.get("artifact_type")
        or metadata.get("artifact_type")
        or ""
    ).strip().lower()
    if artifact_type in KB_ARTIFACT_TYPES:
        return BRIDGE_PERSONAL_KB_LAYER
    if artifact_type in WORLD_ARTIFACT_TYPES:
        return BRIDGE_WORLD_LAYER
    if artifact_type in DERIVED_ARTIFACT_TYPES:
        return PERSONAL_DERIVED_LAYER
    if artifact_type in RAW_ARTIFACT_TYPES:
        return PERSONAL_RAW_LAYER

    fact_type = str(
        item.get("factType")
        or item.get("fact_type")
        or metadata.get("fact_type")
        or ""
    ).strip().lower()
    if fact_type == "world":
        return BRIDGE_WORLD_LAYER
    if fact_type in {"observation", "opinion", "mental_model"}:
        return PERSONAL_DERIVED_LAYER

    grounding_status = str(
        item.get("groundingStatus")
        or item.get("grounding_status")
        or metadata.get("grounding_status")
        or ""
    ).strip().lower()
    if grounding_status in {"grounded_derived", "ungrounded_derived"}:
        return PERSONAL_DERIVED_LAYER

    return PERSONAL_RAW_LAYER


def layer_sort_key(item: dict[str, Any], *, consumer: ContextConsumer = "llm_agent") -> tuple[int, float]:
    policy = get_context_policy(consumer)
    layer = normalize_context_layer(item)
    try:
        layer_idx = policy.layer_order.index(layer)
    except ValueError:
        layer_idx = len(policy.layer_order)

    relevance_raw = item.get("relevance")
    try:
        relevance = float(relevance_raw)
    except (TypeError, ValueError):
        relevance = 0.0
    return layer_idx, -relevance


def build_degradation_flags(
    *,
    source_layer_counts: dict[str, int],
    context_blocks: list[dict[str, Any]],
    kg_node_count: int | None = None,
) -> list[str]:
    flags: list[str] = []
    personal_total = int(source_layer_counts.get(PERSONAL_RAW_LAYER, 0)) + int(
        source_layer_counts.get(PERSONAL_DERIVED_LAYER, 0)
    )
    if personal_total == 0:
        flags.append("NO_PERSONAL_MEMORY")
    if int(source_layer_counts.get(BRIDGE_PERSONAL_KB_LAYER, 0)) == 0:
        flags.append("NO_PERSONAL_KB")
    if int(source_layer_counts.get(BRIDGE_WORLD_LAYER, 0)) == 0:
        flags.append("NO_WORLD_EVIDENCE")
    if kg_node_count is not None and kg_node_count <= 0:
        flags.append("NO_WORLD_KG")
    if any(
        normalize_context_layer(block) == BRIDGE_WORLD_LAYER
        and str(block.get("status") or "").strip().lower() in {"conflict", "conflicting", "contested"}
        for block in context_blocks
    ):
        flags.append("WORLD_CLAIM_CONFLICT")
    return flags


def derive_context_tier(block: dict[str, Any]) -> str:
    layer = normalize_context_layer(block)
    status = str(block.get("status") or "").strip().lower()
    grounding = str(block.get("groundingStatus") or block.get("grounding_status") or "").strip().lower()
    try:
        relevance = float(block.get("relevance") or 0.0)
    except (TypeError, ValueError):
        relevance = 0.0

    if status in {"candidate", "stale", "contested", "conflict", "conflicting"}:
        return "L3"
    if layer in {WORKING_MEMORY_LAYER, WORLD_KG_LAYER}:
        return "L0"
    if layer in {PERSONAL_DERIVED_LAYER, PERSONAL_RAW_LAYER}:
        # Grounded derived content (explicit evidence backlinks per
        # exec-memory §3b) promotes to L0 regardless of relevance score —
        # grounding beats heuristic relevance. Ungrounded/unknown stays
        # relevance-gated.
        if grounding in {"grounded_derived", "grounded"}:
            return "L0"
        return "L0" if relevance >= 0.75 else "L1"
    if layer in {BRIDGE_PERSONAL_KB_LAYER, BRIDGE_WORLD_LAYER}:
        return "L2"
    return "L3"


def apply_context_policy(
    blocks: list[dict[str, Any]],
    *,
    consumer: ContextConsumer = "llm_agent",
    kg_node_count: int | None = None,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    policy = get_context_policy(consumer)
    filtered: list[tuple[int, dict[str, Any]]] = []

    for idx, raw_block in enumerate(blocks):
        block = dict(raw_block or {})
        layer = normalize_context_layer(block)
        if layer not in policy.allowed_layers:
            continue

        block["sourceLayer"] = layer

        grounding_status = str(
            block.get("groundingStatus") or block.get("grounding_status") or ""
        ).strip().lower()
        if layer == PERSONAL_DERIVED_LAYER and grounding_status == "ungrounded_derived":
            status = str(block.get("status") or "").strip().lower()
            if not status or status == "available":
                block["status"] = "candidate"
        if policy.require_grounded_derived and layer == PERSONAL_DERIVED_LAYER:
            if grounding_status == "ungrounded_derived":
                continue

        if layer in {WORLD_KG_LAYER, BRIDGE_WORLD_LAYER}:
            status = str(block.get("status") or "").strip()
            provenance = str(block.get("provenanceRef") or block.get("provenance_ref") or "").strip()
            if policy.require_world_status and not status:
                continue
            if policy.require_world_provenance and not provenance:
                continue

        block["contextTier"] = derive_context_tier(block)

        filtered.append((idx, block))

    filtered.sort(key=lambda pair: (layer_sort_key(pair[1], consumer=consumer), pair[0]))
    if limit is not None:
        filtered = filtered[:limit]

    ordered = [block for _, block in filtered]
    counts = Counter(str(block.get("sourceLayer") or normalize_context_layer(block)) for block in ordered)
    flags = build_degradation_flags(
        source_layer_counts=dict(counts),
        context_blocks=ordered,
        kg_node_count=kg_node_count,
    )
    return ordered, dict(counts), flags
