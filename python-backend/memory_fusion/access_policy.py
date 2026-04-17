"""Memory access policies for runtime consumers and write-paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from memory_fusion.semantics import (
    BRIDGE_PERSONAL_KB_LAYER,
    BRIDGE_WORLD_LAYER,
    PERSONAL_DERIVED_LAYER,
    PERSONAL_RAW_LAYER,
    enrich_metadata_with_semantics,
)

MemoryConsumer = Literal["llm_agent", "frontend_ui", "agent_writer", "background_worker", "admin_debug"]


@dataclass(frozen=True)
class MemoryAccessPolicy:
    consumer: MemoryConsumer
    allowed_read_layers: frozenset[str]
    allowed_write_layers: frozenset[str]
    allow_ungrounded_derived: bool = False


ALL_MEMORY_LAYERS = frozenset(
    {
        PERSONAL_RAW_LAYER,
        PERSONAL_DERIVED_LAYER,
        BRIDGE_PERSONAL_KB_LAYER,
        BRIDGE_WORLD_LAYER,
    }
)


MEMORY_ACCESS_POLICIES: dict[MemoryConsumer, MemoryAccessPolicy] = {
    "llm_agent": MemoryAccessPolicy(
        consumer="llm_agent",
        allowed_read_layers=ALL_MEMORY_LAYERS,
        allowed_write_layers=frozenset({PERSONAL_RAW_LAYER, PERSONAL_DERIVED_LAYER}),
        allow_ungrounded_derived=False,
    ),
    "frontend_ui": MemoryAccessPolicy(
        consumer="frontend_ui",
        allowed_read_layers=ALL_MEMORY_LAYERS,
        allowed_write_layers=frozenset(),
        allow_ungrounded_derived=True,
    ),
    "agent_writer": MemoryAccessPolicy(
        consumer="agent_writer",
        allowed_read_layers=ALL_MEMORY_LAYERS,
        allowed_write_layers=frozenset({PERSONAL_RAW_LAYER, PERSONAL_DERIVED_LAYER}),
        allow_ungrounded_derived=False,
    ),
    "background_worker": MemoryAccessPolicy(
        consumer="background_worker",
        allowed_read_layers=ALL_MEMORY_LAYERS,
        allowed_write_layers=frozenset({PERSONAL_RAW_LAYER, PERSONAL_DERIVED_LAYER}),
        allow_ungrounded_derived=False,
    ),
    "admin_debug": MemoryAccessPolicy(
        consumer="admin_debug",
        allowed_read_layers=ALL_MEMORY_LAYERS,
        allowed_write_layers=frozenset(),
        allow_ungrounded_derived=True,
    ),
}


def get_memory_access_policy(consumer: str | None = None) -> MemoryAccessPolicy:
    key = str(consumer or "agent_writer").strip().lower()
    return MEMORY_ACCESS_POLICIES.get(key, MEMORY_ACCESS_POLICIES["agent_writer"])


def normalize_memory_layer(item: dict[str, Any] | None) -> str:
    metadata = dict((item or {}).get("metadata") or (item or {}).get("document_metadata") or {})
    if metadata.get("memory_layer"):
        return str(metadata["memory_layer"])
    enriched = enrich_metadata_with_semantics(
        metadata,
        fact_type=str((item or {}).get("fact_type") or metadata.get("fact_type") or ""),
    )
    return str(enriched.get("memory_layer") or "")


def can_read_item(item: dict[str, Any], *, consumer: str | None = None) -> bool:
    policy = get_memory_access_policy(consumer)
    return normalize_memory_layer(item) in policy.allowed_read_layers


def can_write_item(item: dict[str, Any], *, consumer: str | None = None) -> bool:
    policy = get_memory_access_policy(consumer)
    return normalize_memory_layer(item) in policy.allowed_write_layers


def assert_write_allowed(item: dict[str, Any], *, consumer: str | None = None) -> None:
    if can_write_item(item, consumer=consumer):
        return
    layer = normalize_memory_layer(item) or "unknown"
    policy = get_memory_access_policy(consumer)
    raise ValueError(
        f"memory_fusion access policy rejected write of {layer} for consumer {policy.consumer}"
    )
