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

logger = logging.getLogger(__name__)


async def get_user_api_key(user_id: str, provider: str) -> str | None:
    """Holt decrypted API Key aus DB. None wenn nicht gesetzt."""
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return None

    try:
        import psycopg

        from agent.security.key_vault import get_vault

        vault = get_vault()
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            row = await (await conn.execute(
                "SELECT credential_enc FROM agent.user_credentials "
                "WHERE user_id = %s AND category = 'llm' AND provider_id = %s AND is_valid = true",
                (user_id, provider),
            )).fetchone()

            if row and row[0]:
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
            row = await (await conn.execute(
                "SELECT default_model FROM agent.user_llm_settings WHERE user_id = %s",
                (user_id,),
            )).fetchone()

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
            row = await (await conn.execute(
                "SELECT per_role_overrides FROM agent.user_llm_settings WHERE user_id = %s",
                (user_id,),
            )).fetchone()

            if row and row[0] and isinstance(row[0], dict):
                return row[0].get(role)
    except Exception as e:
        logger.warning("get_user_role_model failed for %s/%s: %s", user_id, role, e)

    return None


def get_env_default_model() -> str:
    """Fallback: AGENT_DEFAULT_UTILITY_MODEL aus ENV."""
    return os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "")


def provider_from_model(model: str) -> str:
    """Extrahiert Provider aus Model-Name. 'anthropic/claude-sonnet-4-6' -> 'anthropic'."""
    if "/" in model:
        return model.split("/")[0]
    return ""
