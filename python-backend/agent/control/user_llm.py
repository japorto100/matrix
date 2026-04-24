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
from typing import Any, TypedDict

import httpx
from fastapi import APIRouter, HTTPException, Request

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

PROVIDER_REGISTRY: dict[str, dict[str, Any]] = {
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
    # Aggregator — openrouter/auto and openrouter/free are ROUTERS, not models.
    # They are handled as special mode values, not listed in models[].
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
    meta = PROVIDER_REGISTRY.get(provider_id)
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

    # default_mode + default_reasoning_effort from DB
    default_mode = "auto"
    default_reasoning_effort = "medium"
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if db_url:
        try:
            import psycopg

            async with await psycopg.AsyncConnection.connect(db_url) as conn:
                row = await (
                    await conn.execute(
                        "SELECT default_mode, default_reasoning_effort FROM agent.user_llm_settings WHERE user_id = %s",
                        (user_id,),
                    )
                ).fetchone()
                if row:
                    default_mode = row[0] or "auto"
                    default_reasoning_effort = row[1] or "medium"
        except Exception:
            pass

    providers = []
    for prov_id, meta in PROVIDER_REGISTRY.items():
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
        "default_mode": default_mode,
        "default_reasoning_effort": default_reasoning_effort,
        "providers": providers,
        "routers": [
            {"id": "openrouter/free", "label": "Free (auto-select from free models)", "cost": "free"},
            {"id": "openrouter/auto", "label": "Auto (best model for task)", "cost": "paid"},
        ],
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
    """Store an encrypted API key for a provider + create LiteLLM Virtual Key.

    Flow:
    1. Encrypt and store the real provider key in agent.user_credentials
    2. Create a LiteLLM Virtual Key with budget/rate limits pointing at the provider
    3. Store the virtual key reference in credentials metadata
    4. Agent uses the virtual key at runtime (real key stays hidden in LiteLLM)
    """
    user_id = _user_id(request)
    body = await request.json()
    api_key = body.get("api_key", "")
    max_budget = body.get("max_budget")  # Optional: USD budget limit
    budget_duration = body.get("budget_duration", "monthly")  # monthly | daily | weekly

    if not api_key:
        return {"status": "error", "message": "api_key required"}

    if provider_id not in PROVIDER_REGISTRY:
        return {"status": "error", "message": f"Unknown provider: {provider_id}"}

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"status": "env_only", "message": "No DB — set API key in .env directly"}

    import json

    import psycopg

    from agent.security.key_vault import get_vault

    vault = get_vault()
    encrypted = vault.encrypt(api_key)

    # Create LiteLLM Virtual Key (if LiteLLM is available)
    virtual_key_info = await _create_virtual_key(
        user_id=user_id,
        provider_id=provider_id,
        max_budget=max_budget,
        budget_duration=budget_duration,
    )

    metadata = {}
    if virtual_key_info and "key" in virtual_key_info:
        metadata["virtual_key"] = virtual_key_info["key"]
        if "token" in virtual_key_info:
            metadata["virtual_key_id"] = virtual_key_info["token"]
        if max_budget is not None:
            metadata["max_budget"] = max_budget
            metadata["budget_duration"] = budget_duration

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        await conn.execute(
            """INSERT INTO agent.user_credentials
               (user_id, category, provider_id, credential_enc, metadata, updated_at)
               VALUES (%s, 'llm', %s, %s, %s::jsonb, NOW())
               ON CONFLICT (user_id, category, provider_id)
               DO UPDATE SET credential_enc = %s, metadata = %s::jsonb,
                  is_valid = true, updated_at = NOW()""",
            (
                user_id, provider_id, encrypted,
                json.dumps(metadata), encrypted, json.dumps(metadata),
            ),
        )
        await conn.commit()

    result: dict[str, Any] = {
        "status": "ok",
        "user_id": user_id,
        "provider_id": provider_id,
        "api_key_preview": _mask_key(api_key),
    }
    if virtual_key_info and "key" in virtual_key_info:
        result["virtual_key"] = True
        result["budget"] = {"max_budget": max_budget, "duration": budget_duration}
    return result


async def _create_virtual_key(
    user_id: str,
    provider_id: str,
    max_budget: float | None = None,
    budget_duration: str = "monthly",
) -> dict[str, Any] | None:
    """Create a LiteLLM Virtual Key for this user+provider.

    Returns {"key": "sk-litellm-...", "token": "..."} or None if LiteLLM unavailable.
    """
    litellm_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
    try:
        payload: dict[str, Any] = {
            "models": [f"{provider_id}/*"],
            "metadata": {"user_id": user_id, "provider_id": provider_id},
            "key_alias": f"{user_id}-{provider_id}",
        }
        if max_budget is not None:
            payload["max_budget"] = max_budget
            payload["budget_duration"] = budget_duration

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{litellm_url}/key/generate", json=payload)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(
                "LiteLLM virtual key creation failed: %d %s",
                resp.status_code, resp.text[:200],
            )
            return None
    except Exception as e:
        logger.debug("LiteLLM virtual key creation error: %s", e)
        return None


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

    meta = PROVIDER_REGISTRY.get(provider_id)
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


# ─── Dynamic Model Discovery (exec-19 Stufe 5b) ─────────────────────────────
#
# Provider-agnostic model listing with capabilities, pricing, and filtering.
# OpenRouter is the richest source (500+ models with detailed metadata).
# Other providers contribute their own models via /v1/models or static lists.
# All are normalized into a unified ModelInfo schema.


class ModelInfo(TypedDict, total=False):
    id: str
    name: str
    provider: str
    description: str
    context_length: int
    max_output_tokens: int
    supports_tools: bool
    supports_vision: bool
    supports_reasoning: bool
    supports_structured_output: bool
    supports_streaming: bool
    is_free: bool
    prompt_price_per_mtok: float | None
    completion_price_per_mtok: float | None
    modality: str  # text | text+image | multimodal
    architecture: str | None
    created_at: int | None
    # Reasoning capabilities (dynamic, not hardcoded)
    reasoning_type: str | None  # "effort" | "thinking" | "always_on" | None
    reasoning_levels: list[str] | None  # e.g. ["low","medium","high"] or ["enabled"]


# Detailed model cache: provider → (list[ModelInfo], timestamp)
_detailed_cache: dict[str, tuple[list[ModelInfo], float]] = {}
_DETAIL_CACHE_TTL = 1800  # 30 min for detailed models (fresher than simple cache)


async def _fetch_openrouter_models(api_key: str) -> list[ModelInfo]:
    """Fetch full model details from OpenRouter /api/v1/models."""
    cached = _detailed_cache.get("openrouter")
    if cached and time.time() - cached[1] < _DETAIL_CACHE_TTL:
        return cached[0]

    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models", headers=headers
            )
            resp.raise_for_status()
            data = resp.json()

        models: list[ModelInfo] = []
        for m in data.get("data", []):
            pricing = m.get("pricing", {})
            prompt_price = _parse_price(pricing.get("prompt"))
            completion_price = _parse_price(pricing.get("completion"))
            supported_params = m.get("supported_parameters", [])
            arch = m.get("architecture", {})

            # Derive reasoning capabilities from supported_parameters
            r_type, r_levels = _derive_reasoning_caps_from_openrouter(supported_params)

            models.append(
                ModelInfo(
                    id=m.get("id", ""),
                    name=m.get("name", m.get("id", "")),
                    provider="openrouter",
                    description=m.get("description", "")[:300],
                    context_length=m.get("context_length", 0),
                    max_output_tokens=m.get("top_provider", {}).get(
                        "max_output_tokens", 0
                    ),
                    supports_tools="tools" in supported_params,
                    supports_vision="image" in arch.get("modality", ""),
                    supports_reasoning="reasoning" in supported_params
                    or "include_reasoning" in supported_params,
                    supports_structured_output="response_format" in supported_params
                    or "json_schema" in supported_params,
                    supports_streaming=True,
                    is_free=prompt_price == 0 and completion_price == 0,
                    prompt_price_per_mtok=prompt_price * 1_000_000
                    if prompt_price is not None
                    else None,
                    completion_price_per_mtok=completion_price * 1_000_000
                    if completion_price is not None
                    else None,
                    modality=arch.get("modality", "text->text"),
                    architecture=arch.get("tokenizer"),
                    created_at=m.get("created"),
                    reasoning_type=r_type,
                    reasoning_levels=r_levels,
                )
            )

        _detailed_cache["openrouter"] = (models, time.time())
        logger.info("OpenRouter: fetched %d models", len(models))
        return models
    except Exception as e:
        logger.warning("OpenRouter model fetch failed: %s", e)
        return _detailed_cache.get("openrouter", ([], 0))[0]


def _derive_reasoning_caps_from_openrouter(
    supported_params: list[str],
) -> tuple[str | None, list[str] | None]:
    """Derive reasoning_type from OpenRouter supported_parameters.

    Only used for OpenRouter models. For other providers, use
    _derive_reasoning_caps_from_litellm() which queries LiteLLM's model registry.
    """
    has_reasoning = "reasoning" in supported_params or "include_reasoning" in supported_params
    has_effort = "reasoning_effort" in supported_params

    if not has_reasoning and not has_effort:
        return None, None

    if has_effort:
        return "effort", None

    return "thinking", None


def _derive_reasoning_caps_from_litellm(
    model: str,
) -> tuple[str | None, list[str] | None]:
    """Query LiteLLM's model registry for reasoning capabilities.

    Uses litellm.get_model_info() which returns:
    - supports_reasoning: bool
    - supported_openai_params: list — contains "reasoning_effort" if supported

    This is fully dynamic and provider-agnostic.
    """
    try:
        import litellm as _litellm

        info = _litellm.get_model_info(model=model)
        if not info:
            return None, None

        has_reasoning = info.get("supports_reasoning", False)
        params = info.get("supported_openai_params") or []
        has_effort = "reasoning_effort" in params
        has_thinking = "thinking" in params

        if not has_reasoning and not has_effort and not has_thinking:
            return None, None

        if has_thinking:
            return "thinking", None
        if has_effort:
            return "effort", None

        return "reasoning", None
    except Exception:
        return None, None


def _parse_price(val: str | float | None) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _static_models_to_info(
    provider_id: str, model_ids: list[str]
) -> list[ModelInfo]:
    """Convert static model IDs to ModelInfo using LiteLLM's model registry.

    Queries litellm.get_model_info() for each model to get capabilities
    dynamically. Falls back to minimal info if LiteLLM doesn't know the model.
    """
    meta = PROVIDER_REGISTRY.get(provider_id, {})
    display = meta.get("display_name", provider_id)
    result: list[ModelInfo] = []
    for mid in model_ids:
        model_key = f"{provider_id}/{mid}"
        info = ModelInfo(
            id=model_key,
            name=mid,
            provider=provider_id,
            description=f"{display} model",
            supports_streaming=True,
            is_free=False,
        )

        # Query LiteLLM for dynamic capabilities
        try:
            import litellm as _litellm

            lm_info = _litellm.get_model_info(model=model_key)
            if lm_info:
                info["context_length"] = lm_info.get("max_input_tokens") or lm_info.get("max_tokens", 0)
                info["max_output_tokens"] = lm_info.get("max_output_tokens", 0)
                info["supports_tools"] = lm_info.get("supports_function_calling", False)
                info["supports_vision"] = lm_info.get("supports_vision", False)
                info["supports_reasoning"] = lm_info.get("supports_reasoning", False)

                params = lm_info.get("supported_openai_params") or []
                info["supports_structured_output"] = "response_format" in params

                # Reasoning type from LiteLLM
                r_type, r_levels = _derive_reasoning_caps_from_litellm(model_key)
                info["reasoning_type"] = r_type
                info["reasoning_levels"] = r_levels

                # Pricing
                input_cost = lm_info.get("input_cost_per_token")
                output_cost = lm_info.get("output_cost_per_token")
                if input_cost is not None:
                    info["prompt_price_per_mtok"] = input_cost * 1_000_000
                if output_cost is not None:
                    info["completion_price_per_mtok"] = output_cost * 1_000_000
        except Exception:
            pass  # LiteLLM doesn't know this model — keep minimal info

        result.append(info)
    return result


@router.get("/user/llm/models")
async def list_models(request: Request) -> dict[str, Any]:
    """List available models with capabilities, pricing, and filtering.

    Query params (all optional):
        provider: filter by provider id (openrouter, anthropic, ...)
        free_only: true = only free models
        supports_tools: true = only models with tool calling
        supports_vision: true = only multimodal/vision models
        supports_reasoning: true = only models with reasoning/thinking
        min_context: minimum context window (e.g. 128000)
        search: substring match on id or name (case-insensitive)
        sort_by: price_asc | price_desc | context_desc | name (default: name)
        limit: max results (1-500, default 100)
        offset: pagination offset

    Returns { models: ModelInfo[], total, facets }.
    """
    user_id = _user_id(request)
    q = request.query_params

    from agent.security.credentials import get_user_api_key

    # Collect models from all providers
    all_models: list[ModelInfo] = []

    for prov_id, meta in PROVIDER_REGISTRY.items():
        key = await get_user_api_key(user_id, prov_id)
        if not key:
            env_key_name = meta.get("env_key", "")
            key = os.environ.get(env_key_name, "") or None if env_key_name else None

        if prov_id == "openrouter" and key:
            all_models.extend(await _fetch_openrouter_models(key))
        elif key or meta.get("type") == "local":
            static = meta.get("models", [])
            if static:
                all_models.extend(_static_models_to_info(prov_id, static))

    # ── Filters ───────────────────────────────────────────────────
    provider_filter = q.get("provider", "").strip()
    free_only = q.get("free_only", "").lower() == "true"
    tools_only = q.get("supports_tools", "").lower() == "true"
    vision_only = q.get("supports_vision", "").lower() == "true"
    reasoning_only = q.get("supports_reasoning", "").lower() == "true"
    structured_only = q.get("supports_structured_output", "").lower() == "true"
    min_context = int(q.get("min_context", "0") or "0")
    max_price = float(q.get("max_price", "0") or "0")
    modality_filter = q.get("modality", "").strip().lower()
    min_output = int(q.get("min_output", "0") or "0")
    search = q.get("search", "").strip().lower()

    filtered: list[ModelInfo] = []
    for m in all_models:
        if provider_filter and m.get("provider") != provider_filter:
            continue
        if free_only and not m.get("is_free"):
            continue
        if tools_only and not m.get("supports_tools"):
            continue
        if vision_only and not m.get("supports_vision"):
            continue
        if reasoning_only and not m.get("supports_reasoning"):
            continue
        if structured_only and not m.get("supports_structured_output"):
            continue
        if min_context and (m.get("context_length", 0) or 0) < min_context:
            continue
        if max_price > 0:
            price = m.get("prompt_price_per_mtok")
            if price is not None and price > max_price:
                continue
        if modality_filter and modality_filter not in (m.get("modality", "") or "").lower():
            continue
        if min_output and (m.get("max_output_tokens", 0) or 0) < min_output:
            continue
        if search and search not in (m.get("id", "") + m.get("name", "")).lower():
            continue
        filtered.append(m)

    # ── Sort ──────────────────────────────────────────────────────
    sort_by = q.get("sort_by", "name")
    if sort_by == "price_asc":
        filtered.sort(key=lambda m: m.get("prompt_price_per_mtok") or float("inf"))
    elif sort_by == "price_desc":
        filtered.sort(
            key=lambda m: m.get("prompt_price_per_mtok") or 0, reverse=True
        )
    elif sort_by == "context_desc":
        filtered.sort(key=lambda m: m.get("context_length", 0) or 0, reverse=True)
    else:
        filtered.sort(key=lambda m: m.get("name", "").lower())

    # ── Pagination ────────────────────────────────────────────────
    total = len(filtered)
    limit = min(max(int(q.get("limit", "100") or "100"), 1), 500)
    offset = max(int(q.get("offset", "0") or "0"), 0)
    page = filtered[offset : offset + limit]

    # ── Facets ────────────────────────────────────────────────────
    provider_counts: dict[str, int] = {}
    free_count = 0
    tools_count = 0
    vision_count = 0
    reasoning_count = 0
    for m in all_models:  # facets from UNFILTERED set
        prov = m.get("provider", "unknown")
        provider_counts[prov] = provider_counts.get(prov, 0) + 1
        if m.get("is_free"):
            free_count += 1
        if m.get("supports_tools"):
            tools_count += 1
        if m.get("supports_vision"):
            vision_count += 1
        if m.get("supports_reasoning"):
            reasoning_count += 1

    return {
        "models": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "facets": {
            "providers": [
                {"id": k, "count": v}
                for k, v in sorted(provider_counts.items(), key=lambda x: -x[1])
            ],
            "free_count": free_count,
            "tools_count": tools_count,
            "vision_count": vision_count,
            "reasoning_count": reasoning_count,
            "total_all": len(all_models),
        },
    }


# ─── Selected Models (exec-19 Stufe 5b) ─────────────────────────────────────
# User picks which models they want available in agent-chat Model-Picker.
# Persisted in agent.user_llm_settings.selected_models (jsonb array of model IDs).


@router.get("/user/llm/selected-models")
async def get_selected_models(request: Request) -> dict[str, Any]:
    """Get user's selected model IDs for agent-chat Model-Picker."""
    user_id = _user_id(request)
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"user_id": user_id, "selected_models": []}

    import psycopg

    try:
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            cur = await conn.execute(
                "SELECT selected_models FROM agent.user_llm_settings WHERE user_id = %s",
                (user_id,),
            )
            row = await cur.fetchone()
            models = row[0] if row and row[0] else []
            return {"user_id": user_id, "selected_models": models}
    except Exception as e:
        logger.warning("get_selected_models failed: %s", e)
        return {"user_id": user_id, "selected_models": []}


@router.put("/user/llm/selected-models")
async def set_selected_models(request: Request) -> dict[str, Any]:
    """Set user's selected model IDs. Body: { "models": ["openrouter/anthropic/claude-sonnet-4-6", ...] }"""
    user_id = _user_id(request)
    body = await request.json()
    models = body.get("models", [])

    if not isinstance(models, list):
        return {"status": "error", "message": "models must be a list of strings"}

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"status": "env_only", "message": "No DB — selection requires PostgreSQL"}

    import json

    import psycopg

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        await conn.execute(
            """INSERT INTO agent.user_llm_settings (user_id, selected_models, updated_at)
               VALUES (%s, %s::jsonb, NOW())
               ON CONFLICT (user_id) DO UPDATE SET selected_models = %s::jsonb, updated_at = NOW()""",
            (user_id, json.dumps(models), json.dumps(models)),
        )
        await conn.commit()

    return {"status": "ok", "user_id": user_id, "selected_models": models, "count": len(models)}


# ─── Smart-Routing Config (ADR-001 G6) ──────────────────────────────────────
# User's smart cheap-vs-strong routing policy.
# Persisted in agent.user_llm_settings.smart_routing (jsonb, migration 026).
# Consumed by agent/llm/smart_routing.py via agent/security/credentials.py.
# See ADR-001 for the rollout gate. Enabling this toggle means silent model-
# substitution on "simple" first-turn messages — the Control-UI surface must
# make that clear (G5 frontend indicator is the user-visible disclosure).


_SMART_ROUTING_INT_KEYS = ("max_simple_chars", "max_simple_words")
_SMART_ROUTING_ALLOWED = (
    "enabled",
    "cheap_model",
    *_SMART_ROUTING_INT_KEYS,
)


def _normalize_smart_routing(raw: Any) -> dict[str, Any]:
    """Whitelist + coerce the JSONB payload so bad shapes never reach the DB.

    Returns a fresh dict containing only known keys with strict types. Empty
    cheap_model or disabled → stripped-down `{}` stays valid (feature off).
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    enabled = raw.get("enabled")
    if enabled is not None:
        if isinstance(enabled, str):
            out["enabled"] = enabled.strip().lower() in ("1", "true", "yes", "on")
        else:
            out["enabled"] = bool(enabled)
    cheap = raw.get("cheap_model")
    if isinstance(cheap, str) and cheap.strip():
        # Strip null-bytes (otherwise postgres JSONB write explodes with
        # DataError → HTTP 500 instead of the 400 we want here) + enforce
        # "provider/model" form so the credential pre-flight (G2) can
        # resolve the provider. Bare names like "gpt-4o-mini" would hit
        # _provider_label() → "litellm" → credentials row absent → silent
        # fallback to primary on every turn. Reject at save-time instead.
        normalized = cheap.strip().replace("\x00", "")[:256]
        if "/" not in normalized:
            raise HTTPException(
                status_code=400,
                detail=(
                    "cheap_model must be in 'provider/model' form "
                    "(e.g. 'openai/gpt-4o-mini', 'anthropic/claude-haiku-4-5'). "
                    "Bare model names silently fail the credential check."
                ),
            )
        out["cheap_model"] = normalized
    for k in _SMART_ROUTING_INT_KEYS:
        v = raw.get(k)
        if v is None:
            continue
        try:
            iv = int(v)
        except (TypeError, ValueError):
            continue
        if iv > 0:
            out[k] = iv
    return out


@router.get("/user/llm/smart-routing")
async def get_smart_routing(request: Request) -> dict[str, Any]:
    """Get the user's smart_routing policy dict.

    Returns ``{"user_id": ..., "smart_routing": {...}}`` where
    ``smart_routing`` may be empty (``{}``) meaning "feature off".
    """
    user_id = _user_id(request)
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"user_id": user_id, "smart_routing": {}}

    import psycopg

    try:
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            cur = await conn.execute(
                "SELECT smart_routing FROM agent.user_llm_settings WHERE user_id = %s",
                (user_id,),
            )
            row = await cur.fetchone()
            cfg = row[0] if row and row[0] else {}
            return {"user_id": user_id, "smart_routing": cfg}
    except Exception as e:  # noqa: BLE001
        logger.warning("get_smart_routing failed: %s", e)
        return {"user_id": user_id, "smart_routing": {}}


@router.put("/user/llm/smart-routing")
async def set_smart_routing(request: Request) -> dict[str, Any]:
    """Set the user's smart_routing policy.

    Body: ``{"enabled": true, "cheap_model": "openai/gpt-4o-mini",
    "max_simple_chars": 160, "max_simple_words": 28}``. Any shape that
    doesn't match the whitelist is dropped silently (defence in depth).

    Disabling is ``{"enabled": false}`` or ``{}``. Also clears cached
    get_user_smart_routing_config entry so next turn sees new policy
    immediately (TTL cache would otherwise defer by up to 60s).
    """
    user_id = _user_id(request)
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    normalized = _normalize_smart_routing(body if isinstance(body, dict) else {})

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {
            "status": "env_only",
            "message": "No DB — smart_routing requires PostgreSQL",
        }

    import json

    import psycopg

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        await conn.execute(
            """INSERT INTO agent.user_llm_settings (user_id, smart_routing, updated_at)
               VALUES (%s, %s::jsonb, NOW())
               ON CONFLICT (user_id) DO UPDATE SET smart_routing = %s::jsonb, updated_at = NOW()""",
            (user_id, json.dumps(normalized), json.dumps(normalized)),
        )
        await conn.commit()

    # Invalidate G3 cache so the next turn sees the new policy without
    # waiting for the TTL.
    try:
        from agent.security import credentials as _cred

        _cred._smart_routing_cache.pop(user_id, None)
    except Exception:  # noqa: BLE001
        pass

    return {"status": "ok", "user_id": user_id, "smart_routing": normalized}


# ─── Account-Level Info (exec-19 Stufe 5b follow-up) ─────────────────────────
# Aggregates credits/usage/spend from provider APIs + LiteLLM.
# OpenRouter: GET /key → limit_remaining, usage_monthly
# LiteLLM: GET /key/info → spend, max_budget (requires LITELLM_DATABASE_URL)
# Other providers: dashboard only (no programmatic API)

_account_cache: dict[str, tuple[dict[str, Any], float]] = {}
_ACCOUNT_CACHE_TTL = 60  # 1 min


async def _fetch_openrouter_account(api_key: str) -> dict[str, Any]:
    """Fetch account info from OpenRouter GET /key endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/key",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", resp.json())
        return {
            "provider": "openrouter",
            "limit": data.get("limit"),
            "limit_remaining": data.get("limit_remaining"),
            "usage": data.get("usage"),
            "usage_monthly": data.get("usage_monthly"),
            "is_free_tier": data.get("is_free_tier", False),
            "rate_limit": data.get("rate_limit"),
        }
    except Exception as e:
        logger.debug("OpenRouter account fetch failed: %s", e)
        return {"provider": "openrouter", "error": str(e)[:200]}


async def _fetch_litellm_spend() -> dict[str, Any]:
    """Fetch spend info from LiteLLM GET /key/info (if DB is configured)."""
    litellm_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{litellm_url}/global/spend/report?group_by=api_key")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "source": "litellm",
                    "total_spend_usd": sum(
                        item.get("spend", 0)
                        for item in (data if isinstance(data, list) else [])
                    ),
                    "details": data if isinstance(data, list) else [],
                }
            # Non-200: LiteLLM running but spend endpoint unavailable
            return {
                "source": "litellm",
                "total_spend_usd": None,
                "message": f"LiteLLM spend endpoint returned {resp.status_code}",
            }
    except Exception as e:
        logger.debug("LiteLLM spend fetch failed: %s", e)
        return {"source": "litellm", "error": str(e)[:200]}


@router.get("/user/llm/account-info")
async def get_account_info(request: Request) -> dict[str, Any]:
    """Aggregated account-level info from all providers.

    Returns credits, usage, spend data where available.
    Provider support:
    - OpenRouter: credits remaining, monthly usage, free tier status
    - LiteLLM: aggregated spend across all providers (requires DB)
    - Others: no programmatic API (dashboard only)
    """
    user_id = _user_id(request)

    # Check cache
    cached = _account_cache.get(user_id)
    if cached and time.time() - cached[1] < _ACCOUNT_CACHE_TTL:
        return cached[0]

    from agent.security.credentials import get_user_api_key

    providers_info: list[dict[str, Any]] = []

    # OpenRouter account info
    or_key = await get_user_api_key(user_id, "openrouter")
    if not or_key:
        or_key = os.environ.get("OPENROUTER_API_KEY", "") or None
    if or_key:
        providers_info.append(await _fetch_openrouter_account(or_key))

    # LiteLLM aggregated spend
    litellm_info = await _fetch_litellm_spend()
    providers_info.append(litellm_info)

    result = {
        "user_id": user_id,
        "providers": providers_info,
        "total_spend_usd": litellm_info.get("total_spend_usd"),
    }

    _account_cache[user_id] = (result, time.time())
    return result


# ─── LiteLLM Spend Proxy (exec-19 Stufe 5d) ──────────────────────────────────
# Proxy endpoints to LiteLLM's spend/activity APIs.
# LiteLLM must have LITELLM_DATABASE_URL configured for these to work.


async def _litellm_get(path: str, params: dict[str, str] | None = None) -> Any:
    """Proxy GET to LiteLLM. Returns parsed JSON or error dict."""
    litellm_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{litellm_url}{path}", params=params)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"LiteLLM {resp.status_code}", "detail": resp.text[:300]}
    except Exception as e:
        return {"error": str(e)[:200]}


@router.get("/user/llm/spend/activity")
async def get_spend_activity(request: Request) -> Any:
    """Daily spend + request activity from LiteLLM.

    Query params: start_date, end_date (YYYY-MM-DD). Defaults to last 30 days.
    Returns: [{date, api_requests, total_tokens}] + sums.
    """
    q = request.query_params
    params: dict[str, str] = {}
    if q.get("start_date"):
        params["start_date"] = q["start_date"]
    if q.get("end_date"):
        params["end_date"] = q["end_date"]
    return await _litellm_get("/global/activity", params or None)


@router.get("/user/llm/spend/by-model")
async def get_spend_by_model(request: Request) -> Any:
    """Spend broken down by model from LiteLLM.

    Query params: start_date, end_date (YYYY-MM-DD).
    Returns: [{model, api_requests, total_tokens, ...}] grouped by model_group.
    """
    q = request.query_params
    params: dict[str, str] = {}
    if q.get("start_date"):
        params["start_date"] = q["start_date"]
    if q.get("end_date"):
        params["end_date"] = q["end_date"]
    return await _litellm_get("/global/activity/model", params or None)


@router.get("/user/llm/spend/by-provider")
async def get_spend_by_provider() -> Any:
    """Spend grouped by provider. No DB required (uses router cache)."""
    return await _litellm_get("/global/spend/provider")


# ─── Utility Models Config (exec-19 Stufe 5d) ─────────────────────────────────

UTILITY_PURPOSES = ("summarizer", "embedder_text", "embedder_visual", "reranker", "stt", "tts")


@router.get("/user/llm/utility-models")
async def get_utility_models(request: Request) -> dict[str, Any]:
    """Get user's configured utility models."""
    user_id = _user_id(request)
    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"user_id": user_id, "utility_models": {}}

    import psycopg

    try:
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            row = await (
                await conn.execute(
                    "SELECT utility_models FROM agent.user_llm_settings WHERE user_id = %s",
                    (user_id,),
                )
            ).fetchone()
            models = row[0] if row and row[0] else {}
            return {"user_id": user_id, "utility_models": models}
    except Exception as e:
        logger.warning("get_utility_models failed: %s", e)
        return {"user_id": user_id, "utility_models": {}}


@router.put("/user/llm/utility-models")
async def set_utility_models(request: Request) -> dict[str, Any]:
    """Set utility models. Body: { "summarizer": "model-id", "stt": "whisper-local", ... }"""
    user_id = _user_id(request)
    body = await request.json()

    # Validate keys
    models = {k: v for k, v in body.items() if k in UTILITY_PURPOSES and isinstance(v, str)}

    db_url = os.environ.get("HINDSIGHT_DB_URL")
    if not db_url:
        return {"status": "env_only", "message": "No DB"}

    import json

    import psycopg

    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        await conn.execute(
            """INSERT INTO agent.user_llm_settings (user_id, utility_models, updated_at)
               VALUES (%s, %s::jsonb, NOW())
               ON CONFLICT (user_id) DO UPDATE SET utility_models = %s::jsonb, updated_at = NOW()""",
            (user_id, json.dumps(models), json.dumps(models)),
        )
        await conn.commit()

    return {"status": "ok", "user_id": user_id, "utility_models": models}
