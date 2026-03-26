"""Matrix Agent Bridge — FastAPI Service.

Startet den Matrix Bot Client als Background-Task.
Stellt Health-Endpoint bereit.

Start:
    uv run uvicorn agent_bridge.app:app --host 127.0.0.1 --port 8097 --reload
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from agent_bridge.agent_client import AgentClient
from agent_bridge.config import Config
from agent_bridge.matrix_client import MatrixBotClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Globale Instanzen
config = Config.from_env()
agent_client = AgentClient(config)
_matrix_bot: MatrixBotClient | None = None
_sync_task: asyncio.Task[None] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _matrix_bot, _sync_task

    # Agent-Service Health-Check
    agent_ok = await agent_client.health_check()
    if not agent_ok:
        logger.warning(
            "Agent-Service nicht erreichbar (%s) — Bot startet trotzdem",
            config.agent_service_url,
        )

    # Matrix Bot starten
    _matrix_bot = MatrixBotClient(config, agent_client)
    _sync_task = asyncio.create_task(_matrix_bot.start(), name="matrix-sync")
    logger.info("Matrix bot task started user_id=%s", config.bot_user_id)

    yield

    # Cleanup
    if _matrix_bot:
        await _matrix_bot.stop()
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
    await agent_client.close()
    logger.info("Matrix agent bridge stopped")


app = FastAPI(
    title="matrix-agent-bridge",
    version="0.1.0",
    description="Verbindet Matrix-Räume mit dem Agent-Service",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> JSONResponse:
    agent_ok = await agent_client.health_check()
    return JSONResponse(
        {
            "status": "ok",
            "service": "matrix-agent-bridge",
            "bot_user_id": config.bot_user_id,
            "homeserver": config.homeserver_url,
            "agent_service": config.agent_service_url,
            "agent_reachable": agent_ok,
        }
    )


@app.get("/status")
async def status() -> JSONResponse:
    return JSONResponse(
        {
            "bot_running": _sync_task is not None and not _sync_task.done(),
            "bot_user_id": config.bot_user_id,
            "store_path": config.store_path,
            "mention_only_in_groups": config.mention_only_in_groups,
            "allowed_homeservers": config.allowed_homeservers,
        }
    )
