"""Hindsight Memory Engine Singleton (exec-11).

Lazy-initialized MemoryEngine. Bridged unsere zentrale ENV Config
auf Hindsight's erwartete HINDSIGHT_API_* ENV vars.

Keine hardcoded Werte — alles kommt aus unseren zentralen ENV vars.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_engine = None
_init_failed = False


def _bridge_env() -> None:
    """Mappt unsere zentralen ENV vars auf Hindsight's HINDSIGHT_API_* ENV vars.

    Einmalig beim Init. setdefault = ueberschreibt nicht wenn bereits gesetzt.
    """
    provider = os.environ.get("AGENT_PROVIDER", "anthropic")
    if provider == "openai-compatible":
        provider = "openai"

    # LLM — Key aus unserer zentralen Config
    api_key = os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        os.environ.setdefault("HINDSIGHT_API_LLM_PROVIDER", provider)
        os.environ.setdefault("HINDSIGHT_API_LLM_API_KEY", api_key)
        os.environ.setdefault("HINDSIGHT_API_LLM_MODEL",
                              os.environ.get("AGENT_UTILITY_MODEL", ""))
    else:
        # Kein API Key → DB-only Modus (Recall funktioniert, Retain/Reflect nicht)
        os.environ.setdefault("HINDSIGHT_API_LLM_PROVIDER", "none")
        logger.info("No LLM API key — Hindsight in DB-only mode (no Retain/Reflect)")
    if os.environ.get("OPENAI_BASE_URL"):
        os.environ.setdefault("HINDSIGHT_API_LLM_BASE_URL", os.environ["OPENAI_BASE_URL"])

    # LiteLLM: wenn aktiviert, Hindsight soll auch litellm nutzen
    if os.environ.get("AGENT_USE_LITELLM", "").lower() == "true":
        os.environ.setdefault("HINDSIGHT_API_LLM_PROVIDER", "litellm")

    # Embeddings + Reranker (lokal by default)
    os.environ.setdefault("HINDSIGHT_API_EMBEDDINGS_PROVIDER", "local")
    os.environ.setdefault("HINDSIGHT_API_RERANKER_PROVIDER", "local")

    # DB
    db_url = os.environ.get("HINDSIGHT_DB_URL", "")
    if db_url:
        os.environ.setdefault("HINDSIGHT_API_DATABASE_URL", db_url)

    # Skip verification (wir verifizieren LLM separat)
    os.environ.setdefault("HINDSIGHT_API_SKIP_LLM_VERIFICATION", "true")
    os.environ.setdefault("HINDSIGHT_API_LAZY_RERANKER", "true")


async def get_memory_engine():
    """Gibt die Singleton MemoryEngine Instanz zurueck (lazy init).

    Returns:
        MemoryEngine Instanz oder None wenn Init fehlschlaegt.
    """
    global _engine, _init_failed

    if _engine is not None:
        return _engine

    if _init_failed:
        return None

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        logger.info("HINDSIGHT_DB_URL not set — Memory Engine disabled")
        _init_failed = True
        return None

    try:
        _bridge_env()

        from hindsight_api.engine.memory_engine import MemoryEngine

        # Task Backend: BrokerTaskBackend (default, braucht hindsight-worker Prozess)
        # oder SyncTaskBackend (inline, fuer Dev ohne Worker)
        task_backend = None
        use_sync = os.environ.get("HINDSIGHT_SYNC_TASKS", "").lower() == "true"
        if use_sync:
            from hindsight_api.engine.task_backend import SyncTaskBackend
            task_backend = SyncTaskBackend()
            logger.info("Hindsight: using SyncTaskBackend (consolidation inline, no worker needed)")

        _engine = MemoryEngine(db_url=db_url, task_backend=task_backend)
        await _engine.initialize()
        logger.info("Hindsight Memory Engine initialized (db=%s)", db_url.split("@")[-1])
        return _engine

    except Exception as e:
        logger.warning("Memory Engine init failed (Agent works without memory): %s", e)
        _init_failed = True
        return None


def get_bank_id(user_id: str) -> str:
    """Generiert Bank-ID fuer einen User (1 Bank pro User)."""
    return f"user_{user_id}"
