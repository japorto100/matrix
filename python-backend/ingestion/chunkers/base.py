"""Chunker ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ingestion.core.types import ExtractedChunk, ExtractedDocument


class Chunker(ABC):
    """Abstract base for document chunkers."""

    name: str = ""

    @abstractmethod
    def chunk(self, doc: ExtractedDocument) -> list[ExtractedChunk]:
        """Split document into ExtractedChunks for indexing."""
