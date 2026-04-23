"""Credentials Service — einzige Stelle die User Keys/Model aus DB holt.

Genutzt von:
  - app.py (vor Graph-Start: Key + Model laden)
  - control/user_llm.py (für UI: masked Key anzeigen)

Greift NICHT auf LLM zu. Nur DB + KeyVault.
Kein ENV Fallback fuer Model/Key — alles aus DB (control-ui).
"""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

# ADR-001 G3: in-process TTL cache for smart-routing config.
# Rationale: ``get_user_smart_routing_config`` is called on every
# iteration-0 LLM turn (i.e. first turn of every new chat) for every
# non-anonymous user — including the majority who never opt into
# smart-routing (config = ``{}`` → returns None). Without caching this
# means a fresh Postgres connection open/close per new chat for the
# whole user base, adding latency and conn-pool pressure to cold
# turns. A short TTL (60s) is ample: enablement is an intentional
# config change, not a real-time setting.
_SMART_ROUTING_TTL_SECONDS = 60.0
_smart_routing_cache: dict[str, tuple[float, dict | None]] = {}


def _smart_routing_cache_clear() -> None:
    """Test helper — flush the in-process cache."""
    _smart_routing_cache.clear()


async def get_user_api_key(user_id: str, provider: str) -> str | None:
    """Holt API Key fuer LLM Calls. Bevorzugt LiteLLM Virtual Key (sicherer).

    Priority: Virtual Key (metadata.virtual_key) > Decrypted Provider Key.
    Virtual Key = LiteLLM proxy key mit Budget-Enforcement.
    Provider Key = direkter Provider-Schluessel (Fallback).
    """
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return None

    try:
        import psycopg

        from agent.security.key_vault import get_vault

        vault = get_vault()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            row = await (
                await conn.execute(
                    "SELECT credential_enc, metadata FROM agent.user_credentials "
                    "WHERE user_id = %s AND category = 'llm' AND provider_id = %s AND is_valid = true",
                    (user_id, provider),
                )
            ).fetchone()

            if not row or not row[0]:
                return None

            # Prefer Virtual Key if available (budget-enforced, real key hidden)
            meta = row[1] if row[1] else {}
            if isinstance(meta, dict) and meta.get("virtual_key"):
                return meta["virtual_key"]

            # Fallback: decrypt real provider key
            return vault.decrypt(bytes(row[0]))
    except Exception as e:
        logger.warning("get_user_api_key failed for %s/%s: %s", user_id, provider, e)

    return None


async def get_user_default_model(user_id: str) -> str | None:
    """Holt User's gewaehltes Default-Model aus DB. None wenn nicht gesetzt."""
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return None

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            row = await (
                await conn.execute(
                    "SELECT default_model FROM agent.user_llm_settings WHERE user_id = %s",
                    (user_id,),
                )
            ).fetchone()

            if row and row[0]:
                return row[0]
    except Exception as e:
        logger.warning("get_user_default_model failed for %s: %s", user_id, e)

    return None


async def get_user_role_model(user_id: str, role: str) -> str | None:
    """Holt per-role Model Override aus DB. None wenn kein Override."""
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return None

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            row = await (
                await conn.execute(
                    "SELECT per_role_overrides FROM agent.user_llm_settings WHERE user_id = %s",
                    (user_id,),
                )
            ).fetchone()

            if row and row[0] and isinstance(row[0], dict):
                return row[0].get(role)
    except Exception as e:
        logger.warning("get_user_role_model failed for %s/%s: %s", user_id, role, e)

    return None


def get_env_default_model() -> str:
    """Fallback: AGENT_DEFAULT_UTILITY_MODEL aus ENV."""
    return os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "")


async def user_has_provider_credential(user_id: str, provider: str) -> bool:
    """ADR-001 G2 preflight — does the user have an API key for ``provider``?

    Non-mutating; used by smart-routing BEFORE silently switching the
    model to a provider the user cannot authenticate for. Without this,
    an Anthropic-only user whose simple turn routes to an OpenAI cheap
    model receives a bare 401 from the provider.
    """
    if not user_id or not provider:
        return False
    key = await get_user_api_key(user_id, provider)
    return bool(key)


async def get_user_smart_routing_config(user_id: str) -> dict | None:
    """Return the user's smart_routing policy dict from user_llm_settings.

    Returns ``None`` on DB error, missing user, or empty policy. Callers
    pass the result straight into
    :func:`agent.llm.smart_routing.resolve_model_for_turn`.

    Result is cached in-process for ``_SMART_ROUTING_TTL_SECONDS`` (ADR-001
    G3). The negative result (``None``) is cached too so disabled users
    don't pay the DB round-trip on every new chat.
    """
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url or not user_id:
        return None

    now = time.monotonic()
    cached = _smart_routing_cache.get(user_id)
    if cached is not None:
        expires_at, value = cached
        if expires_at > now:
            return value
        # Expired — fall through to re-fetch. Don't delete yet; if the
        # fetch fails we'd rather keep serving the last known value than
        # thrash on every turn.

    try:
        import psycopg

        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            row = await (
                await conn.execute(
                    "SELECT smart_routing FROM agent.user_llm_settings "
                    "WHERE user_id = %s",
                    (user_id,),
                )
            ).fetchone()
            if row and isinstance(row[0], dict) and row[0]:
                value = row[0]
            else:
                value = None
    except Exception as e:  # noqa: BLE001
        logger.debug(
            "get_user_smart_routing_config failed for %s: %s", user_id, e
        )
        # DB error: keep serving the previously cached value (if any)
        # rather than flipping to None for the TTL window.
        return cached[1] if cached is not None else None

    _smart_routing_cache[user_id] = (now + _SMART_ROUTING_TTL_SECONDS, value)
    return value


def provider_from_model(model: str) -> str:
    """Extrahiert Provider aus Model-Name. 'anthropic/claude-sonnet-4-6' -> 'anthropic'."""
    if "/" in model:
        return model.split("/")[0]
    return ""
