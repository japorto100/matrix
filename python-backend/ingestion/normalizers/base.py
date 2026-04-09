"""Normalizer ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ingestion.core.types import ExtractedDocument


class Normalizer(ABC):
    """Abstract base for document normalizers."""

    name: str = ""

    @abstractmethod
    def normalize(self, doc: ExtractedDocument) -> ExtractedDocument:
        """Clean up extracted document in place (or return new instance)."""
