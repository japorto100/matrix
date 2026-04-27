"""Pydantic Settings for the ingestion pipeline (env-driven)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, Field

_ROOT = Path(__file__).resolve().parents[2]
_ORIGINAL_ENV_KEYS = set(os.environ)


def _load_env_files() -> None:
    """Load python-backend .env files without overriding shell-provided env."""
    file_env: dict[str, str] = {}
    env_base = _ROOT / ".env"
    if env_base.exists():
        file_env.update(
            {key: value for key, value in dotenv_values(env_base).items() if value is not None}
        )

    app_env = os.getenv("APP_ENV", file_env.get("APP_ENV", "development")).strip().lower()
    env_specific = _ROOT / f".env.{app_env}"
    if env_specific.exists():
        file_env.update(
            {
                key: value
                for key, value in dotenv_values(env_specific).items()
                if value is not None
            }
        )

    for key, value in file_env.items():
        if key not in _ORIGINAL_ENV_KEYS:
            os.environ[key] = value


class IngestionConfig(BaseModel):
    """Runtime config for the ingestion worker.

    All fields can be overridden via env vars (see .env.example).
    """

    # ── Database ──────────────────────────────────────────────────────────
    db_url: str = Field(
        default_factory=lambda: os.getenv(
            "INGESTION_DB_URL",
            os.getenv(
                "HINDSIGHT_DB_URL",
                "postgresql://postgres@localhost:5433/hindsight_dev",
            ),
        )
    )

    # ── Storage Gateway (D12 capability-based) ────────────────────────────
    artifact_gateway_base_url: str = Field(
        default_factory=lambda: os.getenv("ARTIFACT_GATEWAY_BASE_URL", "http://127.0.0.1:8090")
    )

    # ── KG Pipeline (Phase 2) ─────────────────────────────────────────────
    kg_pipeline_url: str = Field(
        default_factory=lambda: os.getenv("KG_PIPELINE_URL", "http://127.0.0.1:8099")
    )
    kg_pipeline_enabled: bool = Field(
        default_factory=lambda: os.getenv("KG_PIPELINE_ENABLED", "false").lower() == "true"
    )

    # ── Embedder ──────────────────────────────────────────────────────────
    embedder_provider: str = Field(
        default_factory=lambda: os.getenv("EMBEDDER_PROVIDER", "deterministic")
    )
    embedder_model: str = Field(
        default_factory=lambda: os.getenv(
            "EMBEDDER_MODEL",
            os.getenv(
                "OPENROUTER_EMBEDDING_MODEL",
                "sentence-transformers/all-MiniLM-L6-v2",
            ),
        )
    )
    embedder_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "EMBEDDER_BASE_URL",
            os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )
    )
    embedder_api_key: str = Field(
        default_factory=lambda: os.getenv(
            "EMBEDDER_API_KEY",
            os.getenv("OPENROUTER_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        )
    )

    # ── Chunker ───────────────────────────────────────────────────────────
    chunker_name: str = Field(default_factory=lambda: os.getenv("CHUNKER_NAME", "token"))
    chunker_size: int = Field(default_factory=lambda: int(os.getenv("CHUNKER_SIZE", "500")))
    chunker_overlap: int = Field(default_factory=lambda: int(os.getenv("CHUNKER_OVERLAP", "50")))

    # ── Worker ────────────────────────────────────────────────────────────
    host: str = Field(default_factory=lambda: os.getenv("INGESTION_HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("INGESTION_PORT", "8098")))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


@lru_cache(maxsize=1)
def get_config() -> IngestionConfig:
    """Get the singleton config instance."""
    _load_env_files()
    return IngestionConfig()
