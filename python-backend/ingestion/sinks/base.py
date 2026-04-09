"""Sink ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ingestion.core.types import ExtractedChunk, ExtractedDocument, Job


@dataclass
class SinkResult:
    """Result returned by a sink after writing a chunk batch."""

    sink_name: str
    written: int = 0
    skipped: int = 0
    failed: int = 0
    metadata: dict | None = None


class Sink(ABC):
    """Abstract base for output sinks."""

    name: str = ""

    async def open(self) -> None:
        """Optional setup hook called once before the first write."""

    async def close(self) -> None:
        """Optional teardown hook called after the pipeline completes."""

    @abstractmethod
    async def write_batch(
        self,
        doc: ExtractedDocument,
        chunks: list[ExtractedChunk],
        embeddings: list[list[float]],
        job: Job,
    ) -> SinkResult:
        """Write a batch of chunks (with embeddings) into the storage backend."""
