"""Detector ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DetectionResult:
    """File type detection result."""

    mime_type: str  # e.g. "application/pdf"
    extension: str  # e.g. ".pdf" (with leading dot)
    confidence: float = 1.0


class Detector(ABC):
    """Abstract base for file type detectors."""

    name: str = ""

    @abstractmethod
    def detect(
        self,
        path: Path | None = None,
        data: bytes | None = None,
        filename: str | None = None,
    ) -> DetectionResult:
        """Detect file type from path, bytes, or filename hint."""
