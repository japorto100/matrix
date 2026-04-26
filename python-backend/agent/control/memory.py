"""Control Surface — memory ops + runtime inspector payloads."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from agent.control.context_runtime import build_runtime_inspector, normalize_health
from agent.control.request_scope import get_effective_scope
from memory_fusion.engine import get_bank_id, get_memory_engine, get_memory_provider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "memory"])


def _layer_entry(layer_type: str, provider: str) -> dict[str, Any]:
    return {
        "type": layer_type,
        "provider": provider,
        "health": "unknown",
        "itemCount": 0,
        "lastSyncAt": None,
        "consolidationPending": 0,
    }


def _legacy_health(value: str) -> str:
    if value in {"healthy", "degraded", "offline", "unknown"}:
        return {"healthy": "ok", "degraded": "degraded", "offline": "error", "unknown": "error"}[value]
    return "error"


def _legacy_layer(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": entry.get("type"),
        "provider": entry.get("provider"),
        "health": _legacy_health(str(entry.get("health") or "")),
        "item_count": int(entry.get("itemCount") or 0),
        "last_sync_at": entry.get("lastSyncAt"),
        "consolidation_pending": int(entry.get("consolidationPending") or 0),
    }


@router.get("/memory")
@router.get("/memory/health")
async def get_memory_health(request: Request, user_id: str = "local") -> dict[str, Any]:
    """Memory overview for control-ui.

    The payload intentionally contains:
    - `layers`: stable ops/health cards for the existing UI
    - `ops`: same data grouped explicitly for future consumers
    - `inspector`: semantically enriched runtime/context diagnostics
    """
    scope = get_effective_scope(request, user_id=user_id)
    bank_id = get_bank_id(scope.user_id)
    degraded_reasons: list[str] = []

    memory_provider = get_memory_provider()
    vector_provider = "pgvector"
    episodic_entry = _layer_entry("episodic", memory_provider)
    vector_entry = _layer_entry("vector", vector_provider)
    kg_entry = _layer_entry("kg", "kuzu")

    engine = None
    try:
        engine = await get_memory_engine()
        if engine is None:
            episodic_entry["health"] = "degraded"
            vector_entry["health"] = "degraded"
            degraded_reasons.append("MEMORY_ENGINE_DISABLED")
        else:
            from hindsight_api.models import RequestContext

            req_ctx = RequestContext()
            units_result = await engine.list_memory_units(
                bank_id=bank_id,
                limit=1,
                offset=0,
                request_context=req_ctx,
                consumer="frontend_ui",
            )
            total = int(units_result.get("total", 0))
            episodic_entry["health"] = "healthy"
            episodic_entry["itemCount"] = total
            vector_entry["health"] = "healthy"
            vector_entry["itemCount"] = total
            if hasattr(engine, "get_bank_stats"):
                stats = await engine.get_bank_stats(bank_id, request_context=req_ctx)
                pending = int(stats.get("pending_consolidation", 0))
                episodic_entry["consolidationPending"] = pending
                vector_entry["consolidationPending"] = pending
    except Exception as e:  # noqa: BLE001
        logger.warning("episodic/vector health failed: %s", e)
        episodic_entry["health"] = "offline"
        vector_entry["health"] = "offline"
        degraded_reasons.append("MEMORY_ENGINE_ERROR")

    kg_node_count = 0
    try:
        from memory_engine.kg_store import create_kg_store

        kg = create_kg_store()
        kg_node_count = kg.node_count()
        kg_entry["health"] = normalize_health(kg.status())
        kg_entry["itemCount"] = kg_node_count
    except Exception as e:  # noqa: BLE001
        logger.warning("kg health failed: %s", e)
        kg_entry["health"] = "offline"
        degraded_reasons.append("KG_UNAVAILABLE")

    inspector = await build_runtime_inspector(
        engine=engine,
        user_id=scope.user_id,
        bank_id=bank_id,
        provider=memory_provider,
        kg_node_count=kg_node_count,
    )
    last_sync_at = (
        inspector.get("activeSession", {}).get("updatedAt")
        or inspector.get("activeSession", {}).get("completedAt")
        or inspector.get("activeSession", {}).get("startedAt")
    )
    for entry in (episodic_entry, vector_entry, kg_entry):
        if not entry.get("lastSyncAt"):
            entry["lastSyncAt"] = last_sync_at

    layers = [episodic_entry, kg_entry, vector_entry]
    legacy_layers = [_legacy_layer(entry) for entry in layers]
    degraded = bool(degraded_reasons)

    return {
        "ops": {
            "layers": layers,
            "degraded": degraded,
            "degradedReasons": degraded_reasons,
        },
        "inspector": inspector,
        "queryGate": inspector.get("queryGate", {}),
        "layers": legacy_layers,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "degradedReasons": degraded_reasons,
        "user_id": scope.user_id,
        "userId": scope.user_id,
        "bank_id": bank_id,
        "bankId": bank_id,
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
