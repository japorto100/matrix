"""Chunker registry."""

from __future__ import annotations

from ingestion.chunkers.base import Chunker
from ingestion.chunkers.token_chunker import TokenChunker


class ChunkerRegistry:
    """Get a Chunker by name."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        self._chunkers: dict[str, Chunker] = {
            "token": TokenChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
        }

    def get(self, name: str) -> Chunker:
        if name not in self._chunkers:
            raise ValueError(f"Unknown chunker: {name}")
        return self._chunkers[name]

    def register(self, chunker: Chunker) -> None:
        self._chunkers[chunker.name] = chunker
