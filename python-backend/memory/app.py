from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.responses import JSONResponse
from shared import create_service_app  # noqa: E402
from shared.cache_adapter import create_cache_adapter, TTL_INDICATOR, TTL_SNAPSHOT  # noqa: E402
from memory_engine.models import (  # noqa: E402
    EpisodeCreateRequest,
    EpisodeResponse,
    EpisodesListResponse,
    KGNodesResponse,
    KGQueryRequest,
    KGQueryResponse,
    KGSeedRequest,
    KGSeedResponse,
    KGSyncResponse,
    MemoryHealthResponse,
    VectorAddRequest,
    VectorAddResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorSearchResult,
)
from memory_engine.kg_store import create_kg_store  # noqa: E402
from memory_engine.episodic_store import EpisodicStore  # noqa: E402

# Optional vector store — imported lazily to avoid hard dep at startup
_vector_store_instance = None


def _get_vector_store():
    global _vector_store_instance
    if _vector_store_instance is None:
        try:
            from memory_engine.vector_store import VectorStore  # noqa: F401
            _vector_store_instance = VectorStore()
        except Exception:
            _vector_store_instance = None
    return _vector_store_instance


# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------

app = create_service_app("memory-service")

# Singletons (lazy init on first request avoids slow startup)
_kg_store = None
_episodic_store = None
_cache_adapter = None


def _kg():
    global _kg_store
    if _kg_store is None:
        _kg_store = create_kg_store()
    return _kg_store


def _ep():
    global _episodic_store
    if _episodic_store is None:
        _episodic_store = EpisodicStore()
    return _episodic_store


def _cache():
    global _cache_adapter
    if _cache_adapter is None:
        _cache_adapter = create_cache_adapter()
    return _cache_adapter


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=MemoryHealthResponse)
async def health() -> MemoryHealthResponse:
    kg_status = "unavailable"
    try:
        kg_status = _kg().status()
    except Exception:
        pass

    # Keep /health fast and non-blocking: do not lazily initialize vector store here.
    vec_status = "uninitialized"
    if _vector_store_instance is not None:
        try:
            vec_status = _vector_store_instance.status().get("status", "unavailable")
        except Exception:
            vec_status = "degraded"

    ep_status = "unavailable"
    try:
        ep_status = _ep().status()
    except Exception:
        pass

    cache_backend = "unavailable"
    try:
        cache_backend = _cache().backend_name
    except Exception:
        pass

    return MemoryHealthResponse(
        ok=kg_status in ("ready", "degraded"),
        kg=kg_status,
        vector=vec_status,
        cache=cache_backend,
        episodic=ep_status,
    )


# ---------------------------------------------------------------------------
# KG endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/memory/kg/seed", response_model=KGSeedResponse)
async def kg_seed(request: KGSeedRequest) -> KGSeedResponse:
    result = _kg().seed(force=request.force)
    await _cache().delete("tradeview:memory:kg:sync")
    return KGSeedResponse(
        ok=True,
        seeded=result["seeded"],
        node_count=result["node_count"],
        message="seeded" if result["seeded"] else "already seeded, use force=true to re-seed",
    )


@app.post("/api/v1/memory/kg/query", response_model=KGQueryResponse)
async def kg_query(request: KGQueryRequest) -> KGQueryResponse:
    rows = _kg().query(request.query, request.parameters)
    return KGQueryResponse(ok=True, rows=rows, row_count=len(rows))


@app.get("/api/v1/memory/kg/nodes", response_model=KGNodesResponse)
async def kg_nodes(nodeType: str = "Stratagem", limit: int = 100) -> Any:
    safe_limit = min(limit, 500)
    ck = f"tradeview:memory:kg:nodes:{nodeType}:{safe_limit}"
    hit = await _cache().get(ck)
    if hit is not None:
        return JSONResponse(hit)
    nodes = _kg().get_nodes(nodeType, safe_limit)
    result_data = {"ok": True, "nodes": nodes, "total": len(nodes)}
    await _cache().set(ck, result_data, ttl_seconds=TTL_INDICATOR)
    return JSONResponse(result_data)


@app.get("/api/v1/memory/kg/sync", response_model=KGSyncResponse)
async def kg_sync() -> Any:
    ck = "tradeview:memory:kg:sync"
    hit = await _cache().get(ck)
    if hit is not None:
        return JSONResponse(hit)
    result = _kg().sync_snapshot()
    result_data = {
        "ok": True,
        "snapshot": result["snapshot"],
        "checksum": result["checksum"],
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    await _cache().set(ck, result_data, ttl_seconds=TTL_SNAPSHOT)
    return JSONResponse(result_data)


# ---------------------------------------------------------------------------
# Episode endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/memory/episode", response_model=EpisodeResponse)
async def episode_create(request: EpisodeCreateRequest) -> EpisodeResponse:
    result = _ep().create(
        session_id=request.session_id,
        agent_role=request.agent_role,
        input_json=request.input_json,
        output_json=request.output_json,
        duration_ms=request.duration_ms,
        tools_used=request.tools_used,
        token_count=request.token_count,
        confidence=request.confidence,
        tags=request.tags,
        metadata=request.metadata,
        retain_days=request.retain_days,
    )
    return EpisodeResponse(ok=True, id=result["id"], created_at=result["created_at"])


@app.get("/api/v1/memory/episodes", response_model=EpisodesListResponse)
async def episodes_list(agentRole: str = "", limit: int = 100) -> EpisodesListResponse:
    safe_limit = min(max(1, limit), 1000)
    episodes = _ep().list_episodes(agentRole or None, safe_limit)
    return EpisodesListResponse(ok=True, episodes=episodes, total=len(episodes))


# ---------------------------------------------------------------------------
# Vector search endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/memory/search", response_model=VectorSearchResponse)
async def vector_search(request: VectorSearchRequest) -> VectorSearchResponse:
    vec = _get_vector_store()
    if vec is None:
        return VectorSearchResponse(ok=False, results=[], total=0)
    # Keep live-verify deterministic: bootstrap vector index from KG Stratagems when empty.
    try:
        if vec.count() == 0:
            stratagems = _kg().get_nodes("Stratagem", limit=200)
            if stratagems:
                vec.seed_from_kg(stratagems)
    except Exception:
        pass
    raw_results = vec.search(request.query, n_results=min(request.n_results, 20))
    results = [
        VectorSearchResult(
            id=r["id"],
            text=r["text"],
            distance=r["distance"],
            metadata=r.get("metadata", {}),
        )
        for r in raw_results
    ]
    return VectorSearchResponse(ok=True, results=results, total=len(results))


@app.post("/api/v1/memory/vector/add", response_model=VectorAddResponse)
async def vector_add(request: VectorAddRequest) -> VectorAddResponse:
    vec = _get_vector_store()
    if vec is None:
        return VectorAddResponse(ok=False, id=request.id)
    vec.add(request.id, request.text, request.metadata)
    return VectorAddResponse(ok=True, id=request.id)
