"""Memory engine selection for memory_fusion runtime.

Kopie von `agent/memory/engine.py`, erweitert um den Provider `fusion`.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_engine = None
_init_failed = False
_engine_provider: str | None = None


async def get_memory_engine():
    """Gibt die Singleton Memory-Engine Instanz fuer memory_fusion zurueck."""
    global _engine, _init_failed, _engine_provider

    provider = get_memory_provider()

    if _engine is not None and _engine_provider == provider:
        return _engine

    if _engine_provider != provider:
        _engine = None
        _init_failed = False
        _engine_provider = provider

    if _init_failed:
        return None

    if provider == "disabled":
        logger.info("No memory provider configured for memory_fusion")
        _init_failed = True
        return None

    try:
        if provider == "hindsight":
            db_url = os.environ.get("HINDSIGHT_DB_URL")
            if not db_url:
                logger.info("HINDSIGHT_DB_URL not set — Hindsight disabled")
                _init_failed = True
                return None

            from memory_fusion.providers import create_hindsight_engine

            _engine = await create_hindsight_engine(
                db_url=db_url,
                use_sync_tasks=os.environ.get("HINDSIGHT_SYNC_TASKS", "").lower() == "true",
            )
            logger.info("memory_fusion Hindsight initialized (db=%s)", db_url.split("@")[-1])
            return _engine

        if provider == "mempalace":
            from memory_fusion.mempalace_engine import MempalaceMemoryEngine

            db_url = os.environ.get("MEMPALACE_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
            if not db_url:
                logger.info("MEMPALACE_DB_URL/HINDSIGHT_DB_URL not set — MemPalace disabled")
                _init_failed = True
                return None

            _engine = MempalaceMemoryEngine(
                palace_path=os.environ.get("MEMPALACE_PALACE_PATH", "postgres"),
                db_url=db_url,
            )
            await _engine.initialize()
            logger.info("memory_fusion MemPalace initialized (db=%s)", db_url.split("@")[-1])
            return _engine

        if provider == "fusion":
            from memory_fusion.fusion_engine import FusionMemoryEngine

            db_url = os.environ.get("MEMPALACE_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
            _engine = await FusionMemoryEngine.create(
                db_url=db_url,
                palace_path=os.environ.get("MEMPALACE_PALACE_PATH", "postgres"),
            )
            logger.info(
                "memory_fusion FusionMemoryEngine initialized (db=%s, mempalace=postgres)",
                (db_url or "").split("@")[-1] if db_url else "n/a",
            )
            return _engine

        logger.info("Unsupported memory_fusion provider '%s' — disabled", provider)
        _init_failed = True
        return None

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "memory_fusion init failed for provider '%s' (agent works without memory): %s",
            provider,
            exc,
        )
        _init_failed = True
        return None


def get_bank_id(user_id: str) -> str:
    """Generiert Bank-ID fuer einen User (1 Bank pro User)."""
    return f"user_{user_id}"


def get_memory_provider() -> str:
    """Resolve active memory_fusion provider from env.

    Order:
    1. `AGENT_MEMORY_ENGINE` explicit (`hindsight|mempalace|fusion|auto`)
    2. `auto`: produktiv immer `fusion`, sobald Postgres/Hindsight verfuegbar ist
    3. `mempalace` nur noch explizit oder als reiner Fallback/Parity-Pfad
    4. else `disabled`
    """
    provider = os.environ.get("AGENT_MEMORY_ENGINE", "auto").strip().lower()
    if provider and provider != "auto":
        return provider

    has_hindsight = bool(os.environ.get("HINDSIGHT_DB_URL"))
    has_mempalace = bool(os.environ.get("MEMPALACE_DB_URL") or os.environ.get("HINDSIGHT_DB_URL"))
    if has_hindsight:
        return "fusion"
    if has_mempalace:
        return "mempalace"
    return "disabled"
