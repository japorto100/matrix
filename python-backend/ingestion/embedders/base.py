"""Embedder ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Embedder(ABC):
    """Abstract base for chunk embedders."""

    name: str = ""
    dim: int = 0

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts → list of vectors."""

    def embed_one(self, text: str) -> list[float]:
        """Convenience: embed a single text."""
        return self.embed([text])[0]
