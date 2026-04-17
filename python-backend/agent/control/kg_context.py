"""Control Surface — KG stats plus runtime context inspector."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from agent.control.context_runtime import build_runtime_inspector, normalize_health
from agent.control.request_scope import get_effective_scope
from agent.memory.engine import get_bank_id, get_memory_engine, get_memory_provider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "kg-context"])


def _label_for_node(node: dict[str, Any], node_type: str, idx: int) -> tuple[str, str]:
    if isinstance(node.get("name"), str) and node["name"].strip():
        label = node["name"].strip()
        return str(node.get("id") or f"{node_type}:{idx}"), label
    if isinstance(node.get("label"), str) and node["label"].strip():
        label = node["label"].strip()
        return str(node.get("id") or f"{node_type}:{idx}"), label
    text = str(node.get("node") or node.get("id") or f"{node_type}:{idx}")
    return str(node.get("id") or f"{node_type}:{idx}"), text[:120]


def _recent_nodes(store: Any, *, limit: int = 6) -> list[dict[str, Any]]:
    node_types = (
        "Stratagem",
        "Regime",
        "BTEMarker",
        "TransmissionChannel",
        "Asset",
        "Institution",
    )
    items: list[dict[str, Any]] = []
    per_type = max(1, limit // 3)
    for node_type in node_types:
        try:
            nodes = store.get_nodes(node_type, per_type)
        except Exception:  # noqa: BLE001
            continue
        for idx, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            node_id, label = _label_for_node(node, node_type, idx)
            items.append(
                {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "connectedEdges": 0,
                }
            )
            if len(items) >= limit:
                return items
    return items


@router.get("/kg-context")
async def get_kg_context(request: Request, user_id: str = "local") -> dict[str, Any]:
    scope = get_effective_scope(request, user_id=user_id)
    bank_id = get_bank_id(scope.user_id)
    memory_provider = get_memory_provider()
    degraded_reasons: list[str] = []
    stats = {
        "nodeCount": 0,
        "edgeCount": 0,
        "health": "unknown",
        "lastSyncAt": None,
    }
    recent_nodes: list[dict[str, Any]] = []

    try:
        from memory_engine.kg_store import create_kg_store

        store = create_kg_store()
        stats["nodeCount"] = int(store.node_count())
        stats["health"] = normalize_health(store.status())
        if hasattr(store, "list_edges"):
            stats["edgeCount"] = len(store.list_edges(limit=2000))
        recent_nodes = _recent_nodes(store)
    except Exception as exc:  # noqa: BLE001
        logger.warning("kg-context failed: %s", exc)
        stats["health"] = "offline"
        degraded_reasons.append("KG_UNAVAILABLE")

    engine = None
    try:
        engine = await get_memory_engine()
    except Exception as exc:  # noqa: BLE001
        logger.debug("kg-context memory engine probe failed: %s", exc)

    inspector = await build_runtime_inspector(
        engine=engine,
        user_id=scope.user_id,
        bank_id=bank_id,
        provider=memory_provider,
        kg_node_count=int(stats["nodeCount"]),
    )
    inspector["worldClaims"] = [
        block
        for block in inspector.get("contextBlocks", [])
        if str(block.get("sourceLayer") or "") == "bridge_world"
    ][:6]

    return {
        "stats": stats,
        "recentNodes": recent_nodes,
        "inspector": inspector,
        "degraded": bool(degraded_reasons),
        "degradedReasons": degraded_reasons,
        "userId": scope.user_id,
        "bankId": bank_id,
    }
