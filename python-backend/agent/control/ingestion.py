"""Thin httpx proxy to the ingestion-worker (Port 8098).

D17 decoupling rule: this module MUST NOT import from python-backend/ingestion/.
All communication is via HTTP only.

Routes (mounted under /api/v1/control by router.py):
    POST   /ingest/document
    POST   /ingest/note
    POST   /ingest/link
    GET    /ingestion/status
    GET    /ingestion/jobs/{job_id}
    POST   /ingestion/jobs/{job_id}/retry
"""

from __future__ import annotations

import os
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from agent.control.request_scope import effective_user_id

router = APIRouter(tags=["ingestion"])

INGESTION_WORKER_URL = os.environ.get(
    "INGESTION_WORKER_URL", "http://127.0.0.1:8098"
).rstrip("/")
HTTP_TIMEOUT = float(os.environ.get("INGESTION_PROXY_TIMEOUT_S", "30"))


# ─── Request models (mirror ingestion/worker.py) ────────────────────────────


class IngestDocumentRequest(BaseModel):
    file_id: UUID
    user_id: str = "local"
    tags: list[str] = Field(default_factory=list)
    sinks: list[str] = Field(default_factory=lambda: ["hindsight", "storage"])


class IngestNoteRequest(BaseModel):
    text: str
    user_id: str = "local"
    tags: list[str] = Field(default_factory=list)
    title: str | None = None


class IngestLinkRequest(BaseModel):
    url: str
    user_id: str = "local"
    tags: list[str] = Field(default_factory=list)
    title: str | None = None


# ─── Helper ─────────────────────────────────────────────────────────────────


async def _proxy(method: str, path: str, json: dict | None = None) -> dict:
    url = f"{INGESTION_WORKER_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            r = await client.request(method, url, json=json)
            if r.status_code >= 400:
                raise HTTPException(status_code=r.status_code, detail=r.text)
            return r.json()
    except httpx.ConnectError as e:
        raise HTTPException(
            status_code=503,
            detail=f"ingestion-worker unreachable at {INGESTION_WORKER_URL}: {e}",
        ) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"ingestion-worker error: {e}") from e


# ─── Routes ─────────────────────────────────────────────────────────────────


@router.post("/ingest/document")
async def ingest_document(req: IngestDocumentRequest, request: Request) -> dict:
    payload = req.model_dump(mode="json")
    payload["user_id"] = effective_user_id(request, req.user_id)
    return await _proxy("POST", "/ingest/document", json=payload)


@router.post("/ingest/note")
async def ingest_note(req: IngestNoteRequest, request: Request) -> dict:
    payload = req.model_dump(mode="json")
    payload["user_id"] = effective_user_id(request, req.user_id)
    return await _proxy("POST", "/ingest/note", json=payload)


@router.post("/ingest/link")
async def ingest_link(req: IngestLinkRequest, request: Request) -> dict:
    payload = req.model_dump(mode="json")
    payload["user_id"] = effective_user_id(request, req.user_id)
    return await _proxy("POST", "/ingest/link", json=payload)


@router.post("/ingest/document/{file_id}/reindex")
async def reindex_document(file_id: UUID, req: IngestDocumentRequest, request: Request) -> dict:
    """Hash-based incremental reindex (Phase E — Cursor IDE pattern)."""
    payload = req.model_dump(mode="json")
    payload["user_id"] = effective_user_id(request, req.user_id)
    return await _proxy(
        "POST",
        f"/ingest/document/{file_id}/reindex",
        json=payload,
    )


@router.get("/ingestion/status")
async def ingestion_status() -> dict:
    return await _proxy("GET", "/status")


@router.get("/ingestion/jobs/{job_id}")
async def get_ingestion_job(job_id: UUID) -> dict:
    return await _proxy("GET", f"/jobs/{job_id}")


@router.post("/ingestion/jobs/{job_id}/retry")
async def retry_ingestion_job(job_id: UUID) -> dict:
    return await _proxy("POST", f"/jobs/{job_id}/retry")


@router.get("/ingestion/health")
async def ingestion_worker_health() -> dict:
    """Proxy health check for the ingestion-worker."""
    return await _proxy("GET", "/health")
