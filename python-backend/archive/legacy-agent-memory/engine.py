"""Memory engine selection for Agent runtime.

Default bleibt Hindsight, aber weitere Runtime-Engines koennen aktiviert werden:

- `AGENT_MEMORY_ENGINE=hindsight`
- `AGENT_MEMORY_ENGINE=memory_fusion`
- `AGENT_MEMORY_ENGINE=fusion`
- `AGENT_MEMORY_ENGINE=mempalace`
- `AGENT_MEMORY_ENGINE=auto` (default)

`auto` waehlt Hindsight wenn `HINDSIGHT_DB_URL` gesetzt ist, sonst MemPalace
wenn `MEMPALACE_PALACE_PATH` gesetzt ist.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_engine = None
_init_failed = False
_engine_provider: str | None = None


def _bridge_env() -> None:
    """Mappt LiteLLM Gateway auf Hindsight's HINDSIGHT_API_* ENV vars.

    exec-16: Alles geht ueber LiteLLM (OpenAI-compatible).
    Kein Provider-Dispatching, kein direkter API Key — LiteLLM hat die Keys.
    """
    litellm_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")

    # LLM — immer ueber LiteLLM (OpenAI-compatible)
    # Model kommt aus DB (control-ui). Hindsight braucht ein Model fuer Retain/Reflect,
    # das wird bei Engine-Init gesetzt. Ohne Model = DB-only Modus.
    utility_model = os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "")

    os.environ.setdefault("HINDSIGHT_API_LLM_PROVIDER", "openai")
    os.environ.setdefault("HINDSIGHT_API_LLM_BASE_URL", litellm_url)
    os.environ.setdefault("HINDSIGHT_API_LLM_API_KEY", "sk-litellm")
    if utility_model:
        os.environ.setdefault("HINDSIGHT_API_LLM_MODEL", utility_model)

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
        logger.info("No memory engine configured — memory disabled")
        _init_failed = True
        return None

    try:
        if provider == "hindsight":
            db_url = os.environ.get("HINDSIGHT_DB_URL")
            if not db_url:
                logger.info("HINDSIGHT_DB_URL not set — Hindsight disabled")
                _init_failed = True
                return None

            _bridge_env()

            from hindsight_api.engine.memory_engine import MemoryEngine

            # Task Backend: BrokerTaskBackend (default, braucht hindsight-worker Prozess)
            # oder SyncTaskBackend (inline, fuer Dev ohne Worker)
            task_backend = None
            use_sync = os.environ.get("HINDSIGHT_SYNC_TASKS", "").lower() == "true"
            if use_sync:
                from hindsight_api.engine.task_backend import SyncTaskBackend

                task_backend = SyncTaskBackend()
                logger.info(
                    "Hindsight: using SyncTaskBackend (consolidation inline, no worker needed)"
                )

            _engine = MemoryEngine(db_url=db_url, task_backend=task_backend)
            await _engine.initialize()
            logger.info(
                "Hindsight Memory Engine initialized (db=%s)", db_url.split("@")[-1]
            )
            return _engine

        if provider in {"memory_fusion", "fusion"}:
            db_url = os.environ.get("HINDSIGHT_DB_URL")
            if not db_url:
                logger.info("HINDSIGHT_DB_URL not set — memory_fusion disabled")
                _init_failed = True
                return None

            _bridge_env()

            from memory_fusion.fusion_engine import FusionMemoryEngine

            _engine = await FusionMemoryEngine.create(db_url=db_url)
            logger.info(
                "memory_fusion engine initialized (db=%s)", db_url.split("@")[-1]
            )
            return _engine

        if provider == "mempalace":
            from agent.memory.mempalace_engine import MempalaceMemoryEngine

            palace_path = os.environ.get(
                "MEMPALACE_PALACE_PATH", os.path.expanduser("~/.mempalace/palace")
            )
            _engine = MempalaceMemoryEngine(palace_path=palace_path)
            await _engine.initialize()
            logger.info("MemPalace Memory Engine initialized (palace=%s)", palace_path)
            return _engine

        logger.info("Unsupported memory provider '%s' — memory disabled", provider)
        _init_failed = True
        return None

    except Exception as e:
        logger.warning(
            "Memory Engine init failed for provider '%s' (Agent works without memory): %s",
            provider,
            e,
        )
        _init_failed = True
        return None


def get_bank_id(user_id: str) -> str:
    """Generiert Bank-ID fuer einen User (1 Bank pro User)."""
    return f"user_{user_id}"


def get_memory_provider() -> str:
    """Resolve active memory provider from env.

    Order:
    1. `AGENT_MEMORY_ENGINE` explicit (`hindsight|memory_fusion|fusion|mempalace|auto`)
    2. `auto`: Hindsight if DB configured, else MemPalace if palace path configured
    3. otherwise `disabled`
    """
    provider = os.environ.get("AGENT_MEMORY_ENGINE", "auto").strip().lower()
    if provider and provider != "auto":
        if provider == "fusion":
            return "memory_fusion"
        return provider
    if os.environ.get("HINDSIGHT_DB_URL"):
        return "hindsight"
    if os.environ.get("MEMPALACE_PALACE_PATH"):
        return "mempalace"
    return "disabled"
