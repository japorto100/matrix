"""Control Surface — API/Models Tab backend (Slice 7).

Provides:
  - LLM providers list (Anthropic, OpenAI, Ollama, vLLM, LM Studio, OpenRouter, Azure)
    with api_key_set status (sensitive keys masked)
  - Model routing per Trading Role (default + overrides)
  - Utility models (embedder, reranker, STT, TTS)
  - ENV variables (read-only, sanitized)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter

from agent.roles import TradingRole

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "models"])

# Sensitive env prefixes/keys — values are masked in GET /models/env
SENSITIVE_KEY_PATTERNS = (
    "API_KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PICKLE_KEY",
    "SIGNING_SECRET",
    "AS_TOKEN",
    "HS_TOKEN",
)

# ENV vars to expose in the ApiModelsTab ENV section
EXPOSED_ENV_KEYS = [
    "LITELLM_BASE_URL",
    "AGENT_TOOL_TIMEOUT_SEC",
    "AGENT_MAX_ITERATIONS",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "HINDSIGHT_DB_URL",
    "HINDSIGHT_SYNC_TASKS",
    "INGESTION_WORKER_URL",
    "KG_PIPELINE_URL",
    "EXTRACTION_LAYOUT_URL",
    "ARTIFACT_GATEWAY_BASE_URL",
    "GO_GATEWAY_BASE_URL",
    "OPEN_SANDBOX_URL",
    "OPEN_SANDBOX_API_KEY",
    "MATRIX_HOMESERVER_URL",
    "MATRIX_BOT_ACCESS_TOKEN",
    "MATRIX_E2EE_ENABLED",
    "AGENT_STT_PROVIDER",
    "AGENT_TTS_PROVIDER",
    "NATS_URL",
]


def _is_sensitive(key: str) -> bool:
    up = key.upper()
    return any(p in up for p in SENSITIVE_KEY_PATTERNS)


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••"
    return f"{value[:6]}••••{value[-4:]}"


def _providers() -> list[dict[str, Any]]:
    """System-level provider status derived from the canonical registry in user_llm.

    Per-user status (with user-specific keys) comes from the /user/llm endpoint.
    This endpoint shows the system-wide view based on ENV keys only.
    """
    from agent.control.user_llm import PROVIDER_REGISTRY

    result: list[dict[str, Any]] = []
    for prov_id, meta in PROVIDER_REGISTRY.items():
        env_key_name = meta.get("env_key", "")
        key = os.environ.get(env_key_name, "") if env_key_name else ""
        is_local = meta.get("type") == "local"

        result.append(
            {
                "id": prov_id,
                "display_name": meta["display_name"],
                "type": meta.get("type", "cloud"),
                "api_key_set": bool(key),
                "api_key_preview": _mask(key) if key else None,
                "is_active": bool(key) or is_local,
                "available_models": meta.get("models", []) if key or is_local else [],
            }
        )
    return result


@router.get("/models/providers")
async def list_providers() -> dict[str, Any]:
    items = _providers()
    return {
        "items": items,
        "total": len(items),
        "active": sum(1 for p in items if p["is_active"]),
    }


@router.get("/models/routing")
async def list_model_routing() -> dict[str, Any]:
    """Per-role model routing: defaults + overrides.
    System-Default aus ENV, User-Overrides aus DB (via /user/llm Endpoint)."""
    default_model = ""  # kommt aus DB via /user/llm Endpoint, nicht aus ENV

    routing: list[dict[str, Any]] = []
    for role in TradingRole:
        routing.append(
            {
                "role_id": role.value,
                "model_id": default_model,
                "is_default": True,
            }
        )
    return {"items": routing, "total": len(routing)}


@router.get("/models/utility")
async def list_utility_models() -> dict[str, Any]:
    """Utility models — embedder, reranker, STT, TTS."""
    stt = os.environ.get("AGENT_STT_PROVIDER", "whisper-local")
    tts = os.environ.get("AGENT_TTS_PROVIDER", "piper")
    utility_model = ""  # kommt aus DB via /user/llm Endpoint

    return {
        "items": [
            {
                "purpose": "embedder_text",
                "display_name": "Text Embedder",
                "provider_id": "local-st",
                "model_id": "sentence-transformers/all-MiniLM-L6-v2",
                "is_local": True,
                "is_active": True,
                "notes": "384 dim, CPU, 80MB model",
            },
            {
                "purpose": "embedder_visual",
                "display_name": "Visual Embedder (ColPali)",
                "provider_id": "phase2",
                "model_id": "vidore/colpali-v1.3",
                "is_local": True,
                "is_active": False,
                "notes": "Phase 2 — extraction_layout venv",
            },
            {
                "purpose": "reranker",
                "display_name": "Cross-Encoder Reranker",
                "provider_id": "local-bge",
                "model_id": "BAAI/bge-reranker-v2-m3",
                "is_local": True,
                "is_active": False,
                "notes": "Phase 3 retrieval",
            },
            {
                "purpose": "summarizer",
                "display_name": "Summarizer",
                "provider_id": "litellm",
                "model_id": utility_model,
                "is_local": False,
                "is_active": True,
            },
            {
                "purpose": "stt",
                "display_name": "Speech-to-Text",
                "provider_id": stt,
                "model_id": os.environ.get("WHISPER_MODEL", "base"),
                "is_local": stt == "whisper-local",
                "is_active": True,
            },
            {
                "purpose": "tts",
                "display_name": "Text-to-Speech",
                "provider_id": tts,
                "model_id": tts,
                "is_local": tts == "piper",
                "is_active": True,
            },
        ]
    }


@router.get("/models/env")
async def list_env_vars() -> dict[str, Any]:
    """Return exposed env vars with sensitive masking."""
    items: list[dict[str, Any]] = []
    for key in EXPOSED_ENV_KEYS:
        raw = os.environ.get(key, "")
        sensitive = _is_sensitive(key)
        items.append(
            {
                "key": key,
                "value": _mask(raw) if sensitive and raw else raw,
                "is_sensitive": sensitive,
                "source": "env" if raw else "default",
                "description": None,
            }
        )
    return {"items": items, "total": len(items)}
