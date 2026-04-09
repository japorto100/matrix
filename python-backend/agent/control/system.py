"""Control Surface — System Health Dashboard (Slice 6 backend).

Concurrent health pings to all devstack2 services. Returns per-service status.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "system"])

_startup_ts = time.time()


async def _ping_http(name: str, url: str, tier: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url)
            healthy = r.status_code < 500
        return {
            "id": name,
            "name": name,
            "tier": tier,
            "url": url,
            "health": "healthy" if healthy else "degraded",
            "status_code": r.status_code,
        }
    except httpx.HTTPError as e:
        return {
            "id": name,
            "name": name,
            "tier": tier,
            "url": url,
            "health": "unhealthy",
            "error_message": str(e)[:200],
        }


async def _ping_postgres() -> dict[str, Any]:
    db_url = os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )
    try:
        import psycopg

        with psycopg.connect(db_url, autocommit=True, connect_timeout=3) as conn:
            conn.execute("SELECT 1").fetchone()
        return {
            "id": "postgres",
            "name": "PostgreSQL + pgvector",
            "tier": "infra",
            "port": 5433,
            "health": "healthy",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "id": "postgres",
            "name": "PostgreSQL + pgvector",
            "tier": "infra",
            "port": 5433,
            "health": "unhealthy",
            "error_message": str(e)[:200],
        }


@router.get("/system/health")
async def get_system_health() -> dict[str, Any]:
    """Ping all matrix services concurrently and return health per service."""
    ingestion_url = os.environ.get("INGESTION_WORKER_URL", "http://127.0.0.1:8098")
    kg_pipeline_url = os.environ.get("KG_PIPELINE_URL", "http://127.0.0.1:8099")
    extraction_layout_url = os.environ.get("EXTRACTION_LAYOUT_URL", "http://127.0.0.1:8101")
    go_url = os.environ.get("GO_GATEWAY_BASE_URL", "http://127.0.0.1:8090")
    open_sandbox_url = os.environ.get("OPEN_SANDBOX_URL", "http://127.0.0.1:8100")
    seaweedfs_url = "http://127.0.0.1:8333"
    tuwunel_url = os.environ.get("MATRIX_HOMESERVER_URL", "http://127.0.0.1:8448")

    tasks = [
        _ping_postgres(),
        _ping_http("seaweedfs", seaweedfs_url, "infra"),
        _ping_http("tuwunel", f"{tuwunel_url}/_matrix/client/versions", "infra"),
        _ping_http("go-appservice", f"{go_url}/health", "app"),
        _ping_http("ingestion-worker", f"{ingestion_url}/health", "app"),
        _ping_http("kg-pipeline", f"{kg_pipeline_url}/health", "app"),
        _ping_http("extraction-layout", f"{extraction_layout_url}/health", "app"),
        _ping_http("opensandbox", f"{open_sandbox_url}/health", "app"),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    items: list[dict[str, Any]] = []
    for r in results:
        if isinstance(r, Exception):
            items.append({"id": "unknown", "health": "unknown", "error_message": str(r)[:200]})
        else:
            items.append(r)

    # Include self (agent-service)
    items.append(
        {
            "id": "agent-service",
            "name": "Python Agent Service (this)",
            "tier": "app",
            "port": 8094,
            "health": "healthy",
            "uptime_s": int(time.time() - _startup_ts),
        }
    )

    counts = {"healthy": 0, "degraded": 0, "unhealthy": 0, "unknown": 0}
    for it in items:
        counts[it.get("health", "unknown")] += 1

    return {"items": items, "total": len(items), "counts": counts}
