"""Matrix Agent Bridge — FastAPI Service.

NATS Consumer: empfängt Matrix-Messages von Go Appservice, leitet an Agent weiter.
Go Appservice ist einziger Matrix-Endpunkt (E2BE-Pattern).

Start:
    uv run uvicorn bridge.app:app --host 127.0.0.1 --port 8097 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from bridge.agent_client import AgentClient
from bridge.config import Config
from bridge.nats_handler import NATSHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Globale Instanzen
config = Config.from_env()
agent_client = AgentClient(config)
nats_handler = NATSHandler(config, agent_client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Agent-Service Health-Check
    agent_ok = await agent_client.health_check()
    if not agent_ok:
        logger.warning(
            "Agent-Service nicht erreichbar (%s) — Bridge startet trotzdem",
            config.agent_service_url,
        )

    # NATS verbinden + subscriben
    await nats_handler.connect()
    logger.info("NATS bridge started, agent_user_id=%s", config.agent_user_id)

    yield

    # Cleanup
    await nats_handler.close()
    await agent_client.close()
    logger.info("Matrix agent bridge stopped")


app = FastAPI(
    title="matrix-agent-bridge",
    version="0.2.0",
    description="NATS Consumer — verbindet Go Appservice mit Agent-Service",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> JSONResponse:
    agent_ok = await agent_client.health_check()
    return JSONResponse(
        {
            "status": "ok",
            "service": "matrix-agent-bridge",
            "nats_connected": nats_handler.is_connected,
            "nats_url": config.nats_url,
            "agent_service": config.agent_service_url,
            "agent_reachable": agent_ok,
            "agent_user_id": config.agent_user_id,
        }
    )
