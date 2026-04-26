"""Shared runtime env helpers for memory_fusion."""

from __future__ import annotations

import os


def bridge_hindsight_env() -> None:
    """Mappt LiteLLM-/DB-ENV auf Hindsights erwartete Runtime-Variablen."""
    litellm_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
    utility_model = os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "")
    embedding_provider = os.environ.get("MEMORY_EMBEDDING_PROVIDER", "openrouter").strip().lower()
    if embedding_provider not in {"openrouter", "openai-compatible"}:
        raise RuntimeError(f"Unsupported MEMORY_EMBEDDING_PROVIDER={embedding_provider!r} for Hindsight")
    embedding_model = (
        os.environ.get("MEMORY_EMBEDDING_MODEL")
        or os.environ.get("HINDSIGHT_EMBEDDING_MODEL")
        or os.environ.get("MEMPALACE_EMBEDDING_MODEL")
        or os.environ.get("OPENROUTER_EMBEDDING_MODEL")
        or "sentence-transformers/all-minilm-l6-v2"
    )
    embedding_base_url = os.environ.get(
        "MEMORY_EMBEDDING_BASE_URL",
        os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

    os.environ.setdefault("HINDSIGHT_API_LLM_PROVIDER", "openai")
    os.environ.setdefault("HINDSIGHT_API_LLM_BASE_URL", litellm_url)
    os.environ.setdefault("HINDSIGHT_API_LLM_API_KEY", "sk-litellm")
    if utility_model:
        os.environ.setdefault("HINDSIGHT_API_LLM_MODEL", utility_model)

    os.environ["HINDSIGHT_API_EMBEDDINGS_PROVIDER"] = "openai"
    os.environ["HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL"] = embedding_base_url
    os.environ["HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL"] = embedding_model
    if openrouter_key:
        os.environ["HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY"] = openrouter_key
    os.environ.setdefault("HINDSIGHT_API_RERANKER_PROVIDER", "rrf")

    db_url = os.environ.get("HINDSIGHT_DB_URL", "")
    if db_url:
        os.environ.setdefault("HINDSIGHT_API_DATABASE_URL", db_url)

    os.environ.setdefault("HINDSIGHT_API_SKIP_LLM_VERIFICATION", "true")
    os.environ.setdefault("HINDSIGHT_API_LAZY_RERANKER", "true")
