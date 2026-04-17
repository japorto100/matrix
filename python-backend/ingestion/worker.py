"""Ingestion FastAPI Worker (Port 8098).

Decoupled from main agent runtime (D17). Communication via HTTP only.
"""

from __future__ import annotations

import hmac
import os
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from ingestion.core.config import get_config
from ingestion.core.exceptions import DedupSkipError
from ingestion.core.types import JobStatus
from ingestion.pipelines.base import PipelineContext
from ingestion.pipelines.document import DocumentPipeline
from ingestion.pipelines.link import LinkPipeline
from ingestion.pipelines.note import NotePipeline
from loguru import logger
from pydantic import BaseModel, Field

# Global pipeline context (initialized on startup)
_ctx: PipelineContext | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ctx
    config = get_config()
    logger.info("ingestion-worker starting (port {})", config.port)
    logger.info(
        "  db_url={}",
        config.db_url.split("@")[-1] if "@" in config.db_url else config.db_url,
    )
    logger.info("  artifact_gateway={}", config.artifact_gateway_base_url)
    logger.info("  kg_pipeline_enabled={}", config.kg_pipeline_enabled)
    logger.info("  embedder={}", config.embedder_model)
    _ctx = PipelineContext.from_config(config)

    # Recover any jobs that were stuck mid-pipeline from a previous crash
    try:
        recovered = _ctx.tracker.recover_stuck_jobs()
        if recovered:
            logger.warning("recovered {} stuck jobs (marked as failed)", recovered)
    except Exception as e:  # noqa: BLE001
        logger.warning("recover_stuck_jobs failed (db not yet ready?): {}", e)

    yield

    # Cleanup: close all sinks (release DB connections, model handles)
    logger.info("ingestion-worker shutting down — closing sinks")
    for sink in _ctx.sinks.all():
        try:
            await sink.close()
        except Exception as e:  # noqa: BLE001
            logger.warning("sink {} close failed: {}", sink.name, e)
    logger.info("ingestion-worker stopped")


app = FastAPI(
    title="Matrix Ingestion Worker",
    description="Decoupled extraction pipeline (Venv 2). See exec-15 §5.2 + D13-D17.",
    version="0.1.0",
    lifespan=lifespan,
)


# ─── Service auth (exec-19 Review Fix #8) ─────────────────────────────────
#
# The worker is called by go-appservice over the loopback interface. In
# dev mode no secret is set and unauthenticated calls are accepted. In
# production INGESTION_WORKER_SHARED_SECRET must be set on both sides
# (Go + Python) and every request carries X-Service-Auth: <secret>.
#
# The middleware approach protects all routes except /health with a single
# check. hmac.compare_digest prevents timing attacks.

_SHARED_SECRET = os.getenv("INGESTION_WORKER_SHARED_SECRET", "").strip()
_AUTH_EXEMPT_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})


@app.middleware("http")
async def service_auth_middleware(request: Request, call_next):
    # Dev mode: no secret configured → accept all
    if not _SHARED_SECRET:
        return await call_next(request)
    # Health + docs bypass auth so monitoring + devtools work without secret
    if request.url.path in _AUTH_EXEMPT_PATHS:
        return await call_next(request)
    header = request.headers.get("X-Service-Auth", "")
    if not header or not hmac.compare_digest(header, _SHARED_SECRET):
        return JSONResponse(
            status_code=401,
            content={"detail": "invalid or missing X-Service-Auth"},
        )
    return await call_next(request)


# ─── Request models ────────────────────────────────────────────────────────


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


# ─── Routes ────────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    """Liveness probe — checks DB connectivity."""
    if _ctx is None:
        raise HTTPException(status_code=503, detail="ctx not initialized")
    try:
        _ctx.tracker.status_counts()
        return {"status": "ok", "kg_pipeline_enabled": _ctx.config.kg_pipeline_enabled}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"db unreachable: {e}") from e


@app.post("/ingest/document")
async def ingest_document(
    req: IngestDocumentRequest, background: BackgroundTasks
) -> dict:
    """Trigger document ingestion. Returns job_id immediately, runs async."""
    if _ctx is None:
        raise HTTPException(status_code=503, detail="not initialized")

    pipeline = DocumentPipeline(_ctx)

    async def _run():
        try:
            await pipeline.run(
                file_id=req.file_id,
                user_id=req.user_id,
                tags=req.tags,
                sinks_active=req.sinks,
            )
        except DedupSkipError as e:
            logger.info("dedup skip: {}", e)
        except Exception as e:  # noqa: BLE001
            logger.exception("document pipeline failed: {}", e)

    background.add_task(_run)
    return {"status": "accepted", "file_id": str(req.file_id)}


@app.post("/ingest/note")
async def ingest_note(req: IngestNoteRequest) -> dict:
    """Run note pipeline synchronously (fast, < 5s)."""
    if _ctx is None:
        raise HTTPException(status_code=503, detail="not initialized")
    pipeline = NotePipeline(_ctx)
    try:
        job = await pipeline.run(
            text=req.text, user_id=req.user_id, tags=req.tags, title=req.title
        )
        return {
            "status": "ok",
            "job_id": str(job.id),
            "chunks": job.chunks_done,
            "job_status": job.status.value,
        }
    except DedupSkipError as e:
        return {"status": "dedup_skip", "existing_job_id": e.existing_job_id}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/ingest/link")
async def ingest_link(req: IngestLinkRequest, background: BackgroundTasks) -> dict:
    """Trigger link ingestion (async, may take seconds)."""
    if _ctx is None:
        raise HTTPException(status_code=503, detail="not initialized")
    pipeline = LinkPipeline(_ctx)

    async def _run():
        try:
            await pipeline.run(
                url=req.url, user_id=req.user_id, tags=req.tags, title=req.title
            )
        except DedupSkipError as e:
            logger.info("dedup skip: {}", e)
        except Exception as e:  # noqa: BLE001
            logger.exception("link pipeline failed: {}", e)

    background.add_task(_run)
    return {"status": "accepted", "url": req.url}


@app.get("/status")
async def status() -> dict:
    """Aggregate status counts."""
    if _ctx is None:
        raise HTTPException(status_code=503, detail="not initialized")
    counts = _ctx.tracker.status_counts()
    return {
        "counts": counts,
        "total": sum(counts.values()),
        "done": counts.get("done", 0),
        "failed": counts.get("failed", 0),
        "pending": counts.get("pending", 0),
        "running": sum(
            v
            for k, v in counts.items()
            if k
            in (
                "detecting",
                "loading",
                "extracting",
                "normalizing",
                "chunking",
                "embedding",
                "storing",
            )
        ),
        "skipped_dedup": counts.get("skipped_dedup", 0),
    }


@app.get("/jobs")
async def list_jobs(
    limit: int = 50,
    pipeline: str | None = None,
    status: str | None = None,
    user_id: str | None = None,
) -> dict:
    """List recent ingestion jobs with optional filters.

    Query params:
        limit: max rows (1-500, default 50)
        pipeline: filter by pipeline kind (document/note/link/batch)
        status: filter by status (pending/done/failed/extracting/...)
        user_id: filter by user

    Returns dict with {jobs, total, has_more}.
    Used by control-ui Files tabs to show file lists (exec-19).
    """
    if _ctx is None:
        raise HTTPException(status_code=503, detail="not initialized")
    jobs = _ctx.tracker.list_recent(
        limit=limit, pipeline=pipeline, status=status, user_id=user_id
    )
    return {"jobs": jobs, "total": len(jobs), "has_more": len(jobs) >= limit}


@app.get("/jobs/{job_id}")
async def get_job(job_id: UUID) -> dict:
    if _ctx is None:
        raise HTTPException(status_code=503, detail="not initialized")
    job = _ctx.tracker.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.post("/ingest/document/{file_id}/reindex")
async def smart_reindex_endpoint(
    file_id: UUID, req: IngestDocumentRequest, background: BackgroundTasks
) -> dict:
    """Hash-based incremental reindex (Phase E).

    Re-extracts and only re-embeds chunks whose content hash differs from
    the previously stored manifest. See ingestion/pipelines/document.py
    smart_reindex() for the algorithm.
    """
    if _ctx is None:
        raise HTTPException(status_code=503, detail="not initialized")
    pipeline = DocumentPipeline(_ctx)

    async def _run():
        try:
            await pipeline.smart_reindex(
                file_id=file_id,
                user_id=req.user_id,
                tags=req.tags,
                sinks_active=req.sinks,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("smart_reindex failed: {}", e)

    background.add_task(_run)
    return {"status": "accepted", "file_id": str(file_id), "mode": "incremental"}


@app.post("/jobs/{job_id}/retry")
async def retry_job(job_id: UUID, background: BackgroundTasks) -> dict:
    """Re-run a failed job. Re-uses original file_id from the failed job."""
    if _ctx is None:
        raise HTTPException(status_code=503, detail="not initialized")
    failed = _ctx.tracker.get(job_id)
    if failed is None:
        raise HTTPException(status_code=404, detail="job not found")
    if failed["status"] != JobStatus.FAILED.value:
        raise HTTPException(
            status_code=400, detail=f"job is in state {failed['status']}, not failed"
        )
    if not failed.get("file_id"):
        raise HTTPException(status_code=400, detail="job has no file_id (cannot retry)")

    pipeline = DocumentPipeline(_ctx)

    async def _run():
        try:
            await pipeline.run(
                file_id=UUID(failed["file_id"]),
                user_id=failed["user_id"],
                tags=(failed.get("metadata") or {}).get("tags", []),
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("retry failed: {}", e)

    background.add_task(_run)
    return {"status": "accepted", "retried_job_id": str(job_id)}
