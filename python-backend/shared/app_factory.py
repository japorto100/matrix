"""Vereinfachte App-Factory fuer Matrix-Projekt.

Erstellt eine FastAPI App mit Basis-Middleware (Request-ID, Logging).
Ohne gRPC, OTel, OpenObserve — diese Features bleiben im Hauptprojekt.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request

# Load .env
_root = Path(__file__).resolve().parents[1]
_env_dev = _root / ".env"
if _env_dev.exists():
    load_dotenv(dotenv_path=_env_dev, override=False)


def create_service_app(title: str, version: str = "0.1.0") -> FastAPI:
    """Create FastAPI app with request logging middleware."""
    app = FastAPI(title=title, version=version)

    logger = logging.getLogger(f"matrix.{title}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "").strip() or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            json.dumps({
                "service": title,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            })
        )
        return response

    return app
