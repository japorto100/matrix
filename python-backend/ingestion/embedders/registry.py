"""Embedder registry."""

from __future__ import annotations

from ingestion.embedders.base import Embedder
from ingestion.embedders.sentence_transformer import SentenceTransformerEmbedder


class EmbedderRegistry:
    """Get an Embedder by name."""

    def __init__(self, default_model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self._embedders: dict[str, Embedder] = {
            "sentence_transformer": SentenceTransformerEmbedder(model_name=default_model),
        }

    def get(self, name: str) -> Embedder:
        if name not in self._embedders:
            raise ValueError(f"Unknown embedder: {name}")
        return self._embedders[name]

    def register(self, embedder: Embedder) -> None:
        self._embedders[embedder.name] = embedder
