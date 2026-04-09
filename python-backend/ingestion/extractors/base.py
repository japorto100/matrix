"""DocumentExtractor ABC.

Adopted from paperwatcher/paperwatcher/core/doc_extractor/base.py.
The dataclasses (ExtractedDocument, ExtractedTable, etc.) live in
ingestion.core.types — re-exported here for backwards compat with
1:1 paperwatcher copies.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path

from ingestion.core.types import (
    ExtractedAlgorithm,
    ExtractedChunk,
    ExtractedCodeBlock,
    ExtractedDocument,
    ExtractedFigure,
    ExtractedFormula,
    ExtractedTable,
)

__all__ = [
    "DocumentExtractor",
    "ExtractedAlgorithm",
    "ExtractedChunk",
    "ExtractedCodeBlock",
    "ExtractedDocument",
    "ExtractedFigure",
    "ExtractedFormula",
    "ExtractedTable",
]


class DocumentExtractor(ABC):
    """Abstract base class for extraction backends."""

    name: str = ""
    requires_gpu: bool = False
    requires_model_download: bool = False
    model_size_mb: int = 0

    @abstractmethod
    def extract(self, path: Path) -> ExtractedDocument:
        """Extract structured content from a file."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend's dependencies are installed."""

    def extract_timed(self, path: Path) -> ExtractedDocument:
        """Extract with timing information."""
        t0 = time.perf_counter()
        result = self.extract(path)
        result.extraction_time_s = time.perf_counter() - t0
        return result
