# Shared httpx AsyncClient — Phase 22g+ / ABP.2c
# Singleton pattern: one client per process, connection-pooled, lifespan-managed.
# All tool HTTP calls use get_client() instead of opening a new AsyncClient per call.
# close_client() is called on FastAPI shutdown (app.py lifespan).

from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Return the shared AsyncClient, initialising it on first call."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
            ),
        )
    return _client


async def close_client() -> None:
    """Close the shared AsyncClient. Called on app shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
