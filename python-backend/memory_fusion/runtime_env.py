"""Shared runtime env helpers for memory_fusion."""

from __future__ import annotations

import os


def bridge_hindsight_env() -> None:
    """Mappt LiteLLM-/DB-ENV auf Hindsights erwartete Runtime-Variablen."""
    litellm_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
    utility_model = os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "")

    os.environ.setdefault("HINDSIGHT_API_LLM_PROVIDER", "openai")
    os.environ.setdefault("HINDSIGHT_API_LLM_BASE_URL", litellm_url)
    os.environ.setdefault("HINDSIGHT_API_LLM_API_KEY", "sk-litellm")
    if utility_model:
        os.environ.setdefault("HINDSIGHT_API_LLM_MODEL", utility_model)

    os.environ.setdefault("HINDSIGHT_API_EMBEDDINGS_PROVIDER", "local")
    os.environ.setdefault("HINDSIGHT_API_RERANKER_PROVIDER", "local")

    db_url = os.environ.get("HINDSIGHT_DB_URL", "")
    if db_url:
        os.environ.setdefault("HINDSIGHT_API_DATABASE_URL", db_url)

    os.environ.setdefault("HINDSIGHT_API_SKIP_LLM_VERIFICATION", "true")
    os.environ.setdefault("HINDSIGHT_API_LAZY_RERANKER", "true")
