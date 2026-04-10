"""Control Surface — User LLM Settings (exec-16).

Per-user API key management + model selection + per-role routing.
Keys are AES-256-GCM encrypted in DB (agent.user_credentials).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "user-llm"])

_DEFAULT_USER = "default-dev-user"


def _user_id(request: Request) -> str:
    return request.headers.get("x-auth-user", _DEFAULT_USER)


def _mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "••••"
    return f"{key[:6]}••••{key[-4:]}"


# Provider metadata for key validation
_PROVIDER_META: dict[str, dict[str, Any]] = {
    "anthropic": {
        "display_name": "Anthropic",
        "validate_url": None,  # uses SDK
        "models": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    },
    "openai": {
        "display_name": "OpenAI",
        "validate_url": None,
        "models": ["gpt-4o", "gpt-4o-mini"],
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "validate_url": "https://openrouter.ai/api/v1",
        "models": ["anthropic/claude-sonnet-4-6", "openai/gpt-4o", "qwen/qwen3-480b:free"],
    },
    "gemini": {
        "display_name": "Google Gemini",
        "validate_url": None,
        "models": ["gemini-2.5-pro", "gemini-2.5-flash"],
    },
}


@router.get("/user/llm")
async def get_user_llm_settings(request: Request) -> dict[str, Any]:
    """Get user's LLM settings (default model, per-role overrides, provider status)."""
    user_id = _user_id(request)

    from agent.security.credentials import (
        get_env_default_model,
        get_user_api_key,
        get_user_default_model,
    )

    default_model = await get_user_default_model(user_id) or get_env_default_model()

    # Build provider status (keys masked)
    providers = []
    for prov_id, meta in _PROVIDER_META.items():
        key = await get_user_api_key(user_id, prov_id)
        # Fallback auf ENV Key
        if not key:
            env_key_name = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
                           "openrouter": "OPENROUTER_API_KEY", "gemini": "GEMINI_API_KEY"}.get(prov_id, "")
            key = os.environ.get(env_key_name, "") or None
        providers.append({
            "id": prov_id,
            "display_name": meta["display_name"],
            "api_key_set": bool(key),
            "api_key_preview": _mask_key(key) if key else None,
            "available_models": meta["models"] if key else [],
        })

    return {
        "user_id": user_id,
        "default_model": default_model,
        "providers": providers,
    }


@router.put("/user/llm/model")
async def set_default_model(request: Request) -> dict[str, Any]:
    """Set user's default LLM model."""
    user_id = _user_id(request)
    body = await request.json()
    model = body.get("model", "claude-sonnet")

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"status": "env_only", "message": "No DB — Model-Konfiguration braucht PostgreSQL"}

    import psycopg
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        await conn.execute(
            """INSERT INTO agent.user_llm_settings (user_id, default_model, updated_at)
               VALUES (%s, %s, NOW())
               ON CONFLICT (user_id) DO UPDATE SET default_model = %s, updated_at = NOW()""",
            (user_id, model, model),
        )
        await conn.commit()

    return {"status": "ok", "user_id": user_id, "default_model": model}


@router.put("/user/llm/roles")
async def set_role_overrides(request: Request) -> dict[str, Any]:
    """Set per-role model overrides."""
    user_id = _user_id(request)
    body = await request.json()
    overrides = body.get("overrides", {})

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"status": "env_only", "message": "No DB — per-role overrides require PostgreSQL"}

    import json

    import psycopg
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        await conn.execute(
            """INSERT INTO agent.user_llm_settings (user_id, per_role_overrides, updated_at)
               VALUES (%s, %s::jsonb, NOW())
               ON CONFLICT (user_id) DO UPDATE SET per_role_overrides = %s::jsonb, updated_at = NOW()""",
            (user_id, json.dumps(overrides), json.dumps(overrides)),
        )
        await conn.commit()

    return {"status": "ok", "user_id": user_id, "per_role_overrides": overrides}


@router.put("/user/llm/key/{provider_id}")
async def set_api_key(provider_id: str, request: Request) -> dict[str, Any]:
    """Store an encrypted API key for a provider."""
    user_id = _user_id(request)
    body = await request.json()
    api_key = body.get("api_key", "")

    if not api_key:
        return {"status": "error", "message": "api_key required"}

    if provider_id not in _PROVIDER_META:
        return {"status": "error", "message": f"Unknown provider: {provider_id}"}

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"status": "env_only", "message": "No DB — set API key in .env directly"}

    import psycopg

    from agent.security.key_vault import get_vault

    vault = get_vault()
    encrypted = vault.encrypt(api_key)

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        await conn.execute(
            """INSERT INTO agent.user_credentials (user_id, category, provider_id, credential_enc, updated_at)
               VALUES (%s, 'llm', %s, %s, NOW())
               ON CONFLICT (user_id, category, provider_id)
               DO UPDATE SET credential_enc = %s, is_valid = true, updated_at = NOW()""",
            (user_id, provider_id, encrypted, encrypted),
        )
        await conn.commit()

    return {
        "status": "ok",
        "user_id": user_id,
        "provider_id": provider_id,
        "api_key_preview": _mask_key(api_key),
    }


@router.delete("/user/llm/key/{provider_id}")
async def delete_api_key(provider_id: str, request: Request) -> dict[str, Any]:
    """Delete a stored API key."""
    user_id = _user_id(request)

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"status": "env_only", "message": "No DB"}

    import psycopg
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        await conn.execute(
            "DELETE FROM agent.user_credentials WHERE user_id = %s AND category = 'llm' AND provider_id = %s",
            (user_id, provider_id),
        )
        await conn.commit()

    return {"status": "ok", "user_id": user_id, "provider_id": provider_id}


@router.post("/user/llm/key/{provider_id}/validate")
async def validate_api_key(provider_id: str, request: Request) -> dict[str, Any]:
    """Test if an API key is valid by making a minimal LLM call."""
    body = await request.json()
    api_key = body.get("api_key", "")

    if not api_key:
        return {"valid": False, "error": "api_key required"}

    # Validation ueber LiteLLM — ein Pfad fuer alle Provider.
    # Der Key wird temporaer als api_key an den LiteLLM-kompatiblen Endpoint geschickt.
    try:
        from openai import AsyncOpenAI

        meta = _PROVIDER_META.get(provider_id, {})
        base_url = meta.get("validate_url")

        # Fuer Provider die ueber LiteLLM gehen: direkt testen
        # Fuer Provider mit eigener URL (OpenRouter): direkt an deren API
        if not base_url:
            # Direkt-Provider (Anthropic, OpenAI, Gemini) — ueber deren native API testen
            # Wir nutzen OpenAI SDK weil alle diese Provider OpenAI-kompatibel sind via LiteLLM
            from agent.llm_client import get_litellm_client
            client = get_litellm_client()
            probe_model = meta.get("models", [""])[0] if meta.get("models") else ""
            if not probe_model:
                return {"valid": False, "error": f"No probe model for {provider_id}"}
            # Prefix mit provider fuer LiteLLM routing
            if "/" not in probe_model:
                probe_model = f"{provider_id}/{probe_model}"
        else:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            probe_model = meta.get("models", [""])[0] if meta.get("models") else "openai/gpt-4o-mini"

        await client.chat.completions.create(
            model=probe_model,
            max_tokens=5,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return {"valid": True, "models": meta.get("models", [])}

    except Exception as e:
        logger.warning("API key validation failed for %s: %s", provider_id, e)
        return {"valid": False, "error": str(e)[:200]}
