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
    """System-level provider status. Per-user status kommt aus /user/llm Endpoint."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    return [
        {
            "id": "anthropic",
            "display_name": "Anthropic",
            "type": "cloud",
            "api_key_set": bool(anthropic_key),
            "api_key_preview": _mask(anthropic_key) if anthropic_key else None,
            "is_active": bool(anthropic_key),
            "available_models": [
                "claude-opus-4-6",
                "claude-sonnet-4-6",
                "claude-haiku-4-5-20251001",
            ]
            if anthropic_key
            else [],
        },
        {
            "id": "openai",
            "display_name": "OpenAI",
            "type": "cloud",
            "api_key_set": bool(openai_key),
            "api_key_preview": _mask(openai_key) if openai_key else None,
            "is_active": bool(openai_key),
            "available_models": [
                "gpt-4o",
                "gpt-4o-mini",
                "text-embedding-3-small",
            ]
            if openai_key
            else [],
        },
        {
            "id": "ollama",
            "display_name": "Ollama (local)",
            "type": "local",
            "api_key_set": False,
            "endpoint_url": ollama_url or "http://localhost:11434",
            "is_active": False,  # Ollama: aktiv wenn lokal laeuft (health check in Phase 2)
            "available_models": [],
        },
        {
            "id": "vllm",
            "display_name": "vLLM",
            "type": "local",
            "api_key_set": False,
            "endpoint_url": "",
            "is_active": False,
            "available_models": [],
        },
        {
            "id": "lm-studio",
            "display_name": "LM Studio",
            "type": "local",
            "api_key_set": False,
            "endpoint_url": "http://localhost:1234/v1",
            "is_active": False,
            "available_models": [],
        },
        {
            "id": "openrouter",
            "display_name": "OpenRouter",
            "type": "cloud",
            "api_key_set": bool(openrouter_key),
            "api_key_preview": _mask(openrouter_key) if openrouter_key else None,
            "is_active": bool(openrouter_key),
            "available_models": [
                "openrouter/anthropic/claude-sonnet-4-6",
                "openrouter/openai/gpt-4o",
                "openrouter/qwen/qwen3-480b:free",
                "openrouter/meta-llama/llama-3.3-70b-instruct:free",
            ]
            if openrouter_key
            else [],
        },
        {
            "id": "azure-openai",
            "display_name": "Azure OpenAI",
            "type": "cloud",
            "api_key_set": False,
            "is_active": False,
            "available_models": [],
        },
    ]


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
