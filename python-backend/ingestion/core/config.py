"""Pydantic Settings for the ingestion pipeline (env-driven)."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field


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
        default_factory=lambda: os.getenv(
            "ARTIFACT_GATEWAY_BASE_URL", "http://127.0.0.1:8090"
        )
    )

    # ── KG Pipeline (Phase 2) ─────────────────────────────────────────────
    kg_pipeline_url: str = Field(
        default_factory=lambda: os.getenv(
            "KG_PIPELINE_URL", "http://127.0.0.1:8099"
        )
    )
    kg_pipeline_enabled: bool = Field(
        default_factory=lambda: os.getenv("KG_PIPELINE_ENABLED", "false").lower()
        == "true"
    )

    # ── Embedder ──────────────────────────────────────────────────────────
    embedder_provider: str = Field(
        default_factory=lambda: os.getenv("EMBEDDER_PROVIDER", "deterministic")
    )
    embedder_model: str = Field(
        default_factory=lambda: os.getenv(
            "EMBEDDER_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
    )

    # ── Chunker ───────────────────────────────────────────────────────────
    chunker_name: str = Field(
        default_factory=lambda: os.getenv("CHUNKER_NAME", "token")
    )
    chunker_size: int = Field(
        default_factory=lambda: int(os.getenv("CHUNKER_SIZE", "500"))
    )
    chunker_overlap: int = Field(
        default_factory=lambda: int(os.getenv("CHUNKER_OVERLAP", "50"))
    )

    # ── Worker ────────────────────────────────────────────────────────────
    host: str = Field(default_factory=lambda: os.getenv("INGESTION_HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("INGESTION_PORT", "8098")))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


@lru_cache(maxsize=1)
def get_config() -> IngestionConfig:
    """Get the singleton config instance."""
    return IngestionConfig()
