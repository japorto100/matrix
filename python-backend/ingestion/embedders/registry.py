"""Embedder registry."""

from __future__ import annotations

from ingestion.embedders.base import Embedder
from ingestion.embedders.deterministic import DeterministicEmbedder
from ingestion.embedders.openrouter import OpenRouterEmbedder
from ingestion.embedders.sentence_transformer import SentenceTransformerEmbedder


class EmbedderRegistry:
    """Get an Embedder by name."""

    def __init__(
        self,
        default_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        remote_base_url: str | None = None,
        remote_api_key: str | None = None,
    ) -> None:
        self._embedders: dict[str, Embedder] = {
            "sentence_transformer": SentenceTransformerEmbedder(model_name=default_model),
            "deterministic": DeterministicEmbedder(),
            "openrouter": OpenRouterEmbedder(
                model_name=default_model,
                base_url=remote_base_url,
                api_key=remote_api_key,
            ),
        }

    def get(self, name: str) -> Embedder:
        if name not in self._embedders:
            raise ValueError(f"Unknown embedder: {name}")
        return self._embedders[name]

    def register(self, embedder: Embedder) -> None:
        self._embedders[embedder.name] = embedder
