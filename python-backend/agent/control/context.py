"""Control Surface — canonical runtime/prompt context inspector."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from agent.control.context_runtime import build_runtime_inspector, normalize_health
from agent.control.request_scope import get_effective_scope
from memory_fusion.engine import get_bank_id, get_memory_engine, get_memory_provider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "context"])


def _kg_stats() -> dict[str, Any]:
    stats = {
        "nodeCount": 0,
        "edgeCount": 0,
        "health": "unknown",
        "lastSyncAt": None,
    }
    try:
        from memory_engine.kg_store import create_kg_store

        store = create_kg_store()
        stats["nodeCount"] = int(store.node_count())
        stats["health"] = normalize_health(store.status())
        if hasattr(store, "list_edges"):
            stats["edgeCount"] = len(store.list_edges(limit=2000))
    except Exception as exc:  # noqa: BLE001
        logger.warning("context kg stats failed: %s", exc)
        stats["health"] = "offline"
    return stats


@router.get("/context")
async def get_context_inspector(request: Request, user_id: str = "local") -> dict[str, Any]:
    scope = get_effective_scope(request, user_id=user_id)
    bank_id = get_bank_id(scope.user_id)
    memory_provider = get_memory_provider()

    engine = None
    try:
        engine = await get_memory_engine()
    except Exception as exc:  # noqa: BLE001
        logger.debug("context memory engine probe failed: %s", exc)

    kg_stats = _kg_stats()
    inspector = await build_runtime_inspector(
        engine=engine,
        user_id=scope.user_id,
        bank_id=bank_id,
        provider=memory_provider,
        kg_node_count=int(kg_stats["nodeCount"]),
    )
    world_claims = [
        block
        for block in inspector.get("contextBlocks", [])
        if str(block.get("sourceLayer") or "") == "bridge_world"
    ][:6]

    return {
        "stats": {
            "memoryProvider": memory_provider,
            "kgNodeCount": int(kg_stats["nodeCount"]),
            "kgEdgeCount": int(kg_stats["edgeCount"]),
            "kgHealth": kg_stats["health"],
            "hasPersistedRunMetadata": bool(inspector.get("hasPersistedRunMetadata")),
            "liveContextBlockCount": int(inspector.get("liveContextBlockCount") or 0),
        },
        "activeSession": inspector.get("activeSession"),
        "sourceLayerCounts": inspector.get("sourceLayerCounts", {}),
        "contextBlocks": inspector.get("contextBlocks", []),
        "degradationFlags": inspector.get("degradationFlags", []),
        "queryGate": inspector.get("queryGate", {}),
        "worldClaims": world_claims,
        "userId": scope.user_id,
        "bankId": bank_id,
    }
