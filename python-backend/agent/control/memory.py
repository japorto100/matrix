"""Control Surface — Memory Layer Health (Slice 3 backend).

Queries Hindsight's MemoryEngine directly (not the legacy memory_engine/episodic_store.py).
Returns layers in the shape the frontend MemoryHealthCards expects:
  { layers: [{type, provider, health, item_count, last_sync_at, consolidation_pending}, ...] }
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from agent.control.request_scope import get_effective_scope
from agent.memory.engine import get_bank_id, get_memory_engine, get_memory_provider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "memory"])


def _health_to_frontend(health_str: str) -> str:
    """Map backend status strings to frontend MemoryLayer.health (ok|degraded|error)."""
    if health_str in ("ready", "ok"):
        return "ok"
    if health_str in ("degraded", "warning"):
        return "degraded"
    return "error"


@router.get("/memory/health")
async def get_memory_health(request: Request, user_id: str = "local") -> dict[str, Any]:
    """Memory layer health for control-ui MemoryHealthCards.

    Returns the frontend `MemoryOverviewResponse` shape:
      { layers: [{type, provider, health, item_count, last_sync_at,
                   consolidation_pending}, ...] }

    Layer types:
    - episodic: memory_units via Hindsight
    - kg: Trading KG via memory_engine/kg_store.py (Kuzu, Trading domain)
    - vector: pgvector (Hindsight backend, same store)
    """
    scope = get_effective_scope(request, user_id=user_id)
    bank_id = get_bank_id(scope.user_id)
    layers: list[dict[str, Any]] = []

    # ─── Episodic + Vector (both from Hindsight) ────────────────────────────
    memory_provider = get_memory_provider()
    vector_provider = "chromadb" if memory_provider == "mempalace" else "pgvector"

    episodic_entry: dict[str, Any] = {
        "type": "episodic",
        "provider": memory_provider,
        "health": "error",
        "item_count": 0,
        "last_sync_at": None,
        "consolidation_pending": 0,
    }
    vector_entry: dict[str, Any] = {
        "type": "vector",
        "provider": vector_provider,
        "health": "error",
        "item_count": 0,
        "last_sync_at": None,
        "consolidation_pending": 0,
    }
    try:
        engine = await get_memory_engine()
        if engine is None:
            episodic_entry["health"] = "degraded"
            vector_entry["health"] = "degraded"
        else:
            from hindsight_api.models import RequestContext

            req_ctx = RequestContext()
            units_result = await engine.list_memory_units(
                bank_id=bank_id, limit=1, offset=0, request_context=req_ctx
            )
            total = int(units_result.get("total", 0))
            episodic_entry["health"] = "ok"
            episodic_entry["item_count"] = total
            # pgvector shares the backend — same count
            vector_entry["health"] = "ok"
            vector_entry["item_count"] = total
    except Exception as e:  # noqa: BLE001
        logger.warning("episodic/vector health failed: %s", e)

    layers.append(episodic_entry)

    # ─── KG (Trading KG via memory_engine/kg_store.py — NOT legacy) ────────
    kg_entry: dict[str, Any] = {
        "type": "kg",
        "provider": "kuzu",
        "health": "error",
        "item_count": 0,
        "last_sync_at": None,
        "consolidation_pending": 0,
    }
    try:
        from memory_engine.kg_store import create_kg_store

        kg = create_kg_store()
        kg_entry["health"] = _health_to_frontend(kg.status())
        kg_entry["item_count"] = kg.node_count()
    except Exception as e:  # noqa: BLE001
        logger.warning("kg health failed: %s", e)

    layers.append(kg_entry)
    layers.append(vector_entry)

    return {
        "layers": layers,
        "user_id": scope.user_id,
        "bank_id": bank_id,
    }


@router.get("/memory/banks")
async def list_memory_banks(request: Request, user_id: str = "local") -> dict[str, Any]:
    """List memory banks for this user (usually one: user_{user_id})."""
    engine = await get_memory_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Memory engine disabled")

    scope = get_effective_scope(request, user_id=user_id)
    try:
        from hindsight_api.models import RequestContext

        req_ctx = RequestContext()
        banks = await engine.list_banks(request_context=req_ctx)
        banks = [
            b
            for b in banks
            if isinstance(b, dict) and b.get("bank_id") == get_bank_id(scope.user_id)
        ]
        return {"banks": banks, "total": len(banks) if isinstance(banks, list) else 0}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"list_banks failed: {e}") from e
