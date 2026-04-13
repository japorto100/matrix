"""Control Surface — User LLM Settings (exec-16).

Per-user API key management + model selection + per-role routing.
Keys are AES-256-GCM encrypted in DB (agent.user_credentials).

Model Discovery:
- Anthropic: static list (kein /models Endpoint)
- Alle anderen: dynamisch via /v1/models API mit User-Key
- Cache: In-Memory mit 1h TTL
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
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


# ─── Provider Registry ────────────────────────────────────────────────────
# models_endpoint: URL fuer GET /v1/models (None = static list only)
# models: Fallback/static models (Anthropic hat keinen /models Endpoint)
# env_key: ENV var fuer System-Default Key (LiteLLM config liest diese)

_PROVIDER_META: dict[str, dict[str, Any]] = {
    # Cloud US/EU
    "anthropic": {
        "display_name": "Anthropic",
        "type": "cloud",
        "models_endpoint": None,
        "models": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "display_name": "OpenAI",
        "type": "cloud",
        "models_endpoint": "https://api.openai.com/v1/models",
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
        "env_key": "OPENAI_API_KEY",
    },
    "gemini": {
        "display_name": "Google Gemini",
        "type": "cloud",
        "models_endpoint": None,
        "models": ["gemini-2.5-pro", "gemini-2.5-flash"],
        "env_key": "GEMINI_API_KEY",
    },
    "mistral": {
        "display_name": "Mistral",
        "type": "cloud",
        "models_endpoint": "https://api.mistral.ai/v1/models",
        "models": ["mistral-large-latest", "codestral-latest"],
        "env_key": "MISTRAL_API_KEY",
    },
    "groq": {
        "display_name": "Groq",
        "type": "cloud",
        "models_endpoint": "https://api.groq.com/openai/v1/models",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "env_key": "GROQ_API_KEY",
    },
    "cohere": {
        "display_name": "Cohere",
        "type": "cloud",
        "models_endpoint": None,
        "models": ["command-r-plus", "command-r"],
        "env_key": "COHERE_API_KEY",
    },
    # Aggregator
    "openrouter": {
        "display_name": "OpenRouter",
        "type": "cloud",
        "models_endpoint": "https://openrouter.ai/api/v1/models",
        "models": [],
        "env_key": "OPENROUTER_API_KEY",
    },
    # China
    "deepseek": {
        "display_name": "DeepSeek",
        "type": "cloud",
        "models_endpoint": "https://api.deepseek.com/v1/models",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "env_key": "DEEPSEEK_API_KEY",
    },
    "qwen": {
        "display_name": "Qwen (DashScope)",
        "type": "cloud",
        "models_endpoint": None,
        "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
        "env_key": "DASHSCOPE_API_KEY",
    },
    # Local
    "ollama": {
        "display_name": "Ollama",
        "type": "local",
        "models_endpoint": "http://localhost:11434/api/tags",
        "models": [],
        "env_key": None,
    },
    "vllm": {
        "display_name": "vLLM",
        "type": "local",
        "models_endpoint": None,
        "models": [],
        "env_key": None,
    },
    "lmstudio": {
        "display_name": "LM Studio",
        "type": "local",
        "models_endpoint": "http://localhost:1234/v1/models",
        "models": [],
        "env_key": None,
    },
}

# ─── Model Cache (in-memory, 1h TTL) ──────────────────────────────────────
_model_cache: dict[str, tuple[list[str], float]] = {}
_CACHE_TTL = 3600


async def _fetch_provider_models(
    provider_id: str, api_key: str | None = None
) -> list[str]:
    """Fetch available models from provider /v1/models API. Cached 1h."""
    meta = _PROVIDER_META.get(provider_id)
    if not meta:
        return []

    endpoint = meta.get("models_endpoint")
    if not endpoint:
        return meta.get("models", [])

    # Check cache
    cached = _model_cache.get(provider_id)
    if cached and time.time() - cached[1] < _CACHE_TTL:
        return cached[0]

    try:
        headers: dict[str, str] = {}
        if api_key and meta.get("type") != "local":
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(endpoint, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if provider_id == "ollama":
            models = sorted(m["name"] for m in data.get("models", []))
        elif provider_id == "openrouter":
            models = sorted(m["id"] for m in data.get("data", []))
        else:
            models = sorted(m["id"] for m in data.get("data", []))

        _model_cache[provider_id] = (models, time.time())
        return models
    except Exception as e:
        logger.debug("Model fetch for %s failed (using fallback): %s", provider_id, e)
        return meta.get("models", [])


@router.get("/user/llm")
async def get_user_llm_settings(request: Request) -> dict[str, Any]:
    """Get user's LLM settings (default model, per-role overrides, provider status).

    Models werden dynamisch von Provider-APIs geholt (cached 1h).
    Anthropic: statische Liste (kein /models Endpoint).
    """
    user_id = _user_id(request)

    from agent.security.credentials import (
        get_env_default_model,
        get_user_api_key,
        get_user_default_model,
    )

    default_model = await get_user_default_model(user_id) or get_env_default_model()

    providers = []
    for prov_id, meta in _PROVIDER_META.items():
        key = await get_user_api_key(user_id, prov_id)
        if not key:
            env_key_name = meta.get("env_key", "")
            key = os.environ.get(env_key_name, "") or None if env_key_name else None

        # Dynamic models: fetch from provider API if key available
        if key and meta.get("models_endpoint"):
            models = await _fetch_provider_models(prov_id, key)
        elif meta.get("type") == "local" and meta.get("models_endpoint"):
            models = await _fetch_provider_models(prov_id)
        else:
            models = meta.get("models", []) if key else []

        providers.append(
            {
                "id": prov_id,
                "display_name": meta["display_name"],
                "type": meta.get("type", "cloud"),
                "api_key_set": bool(key),
                "api_key_preview": _mask_key(key) if key else None,
                "is_active": bool(key)
                or (meta.get("type") == "local" and len(models) > 0),
                "available_models": models,
            }
        )

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
        return {
            "status": "env_only",
            "message": "No DB — Model-Konfiguration braucht PostgreSQL",
        }

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
        return {
            "status": "env_only",
            "message": "No DB — per-role overrides require PostgreSQL",
        }

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
    """Test if an API key is valid + fetch available models.

    Validation: minimaler LLM-Call ueber LiteLLM mit User-Key.
    Model Discovery: GET /v1/models auf Provider-API mit User-Key.
    """
    body = await request.json()
    api_key = body.get("api_key", "")

    if not api_key:
        return {"valid": False, "error": "api_key required"}

    meta = _PROVIDER_META.get(provider_id)
    if not meta:
        return {"valid": False, "error": f"Unknown provider: {provider_id}"}

    try:
        # Validation: LLM-Call ueber LiteLLM mit extra_body api_key
        from agent.llm_client import get_litellm_client

        client = get_litellm_client()
        probe_model = (meta.get("models") or [""])[0]
        if not probe_model:
            # Kein bekanntes Model — versuche trotzdem zu validieren via model fetch
            models = await _fetch_provider_models(provider_id, api_key)
            if models:
                # Clear cache so next fetch is fresh
                _model_cache.pop(provider_id, None)
                return {"valid": True, "models": models}
            return {"valid": False, "error": f"No probe model for {provider_id}"}

        # LiteLLM routing: model prefix = provider
        if "/" not in probe_model:
            probe_model = f"{provider_id}/{probe_model}"

        await client.chat.completions.create(
            model=probe_model,
            max_tokens=5,
            messages=[{"role": "user", "content": "Hi"}],
            extra_body={"api_key": api_key},
        )

        # Key valid — fetch available models
        _model_cache.pop(provider_id, None)  # clear cache for fresh fetch
        models = await _fetch_provider_models(provider_id, api_key)

        return {"valid": True, "models": models}

    except Exception as e:
        logger.warning("API key validation failed for %s: %s", provider_id, e)
        return {"valid": False, "error": str(e)[:200]}
