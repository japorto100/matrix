"""Detector registry — pick best detector by available info."""

from __future__ import annotations

from pathlib import Path

from ingestion.detectors.base import DetectionResult, Detector
from ingestion.detectors.extension import ExtensionDetector
from ingestion.detectors.magic import MagicDetector


class DetectorRegistry:
    """Smart detection: try magic if data available, else extension."""

    def __init__(self) -> None:
        self._extension = ExtensionDetector()
        try:
            self._magic: MagicDetector | None = MagicDetector()
        except Exception:
            self._magic = None

    def detect(
        self,
        path: Path | None = None,
        data: bytes | None = None,
        filename: str | None = None,
    ) -> DetectionResult:
        # Prefer magic when bytes available — most accurate
        if self._magic is not None and (data is not None or path is not None):
            try:
                return self._magic.detect(path=path, data=data, filename=filename)
            except Exception:
                pass
        return self._extension.detect(path=path, data=data, filename=filename)

    def get(self, name: str) -> Detector:
        """Get a specific detector by name."""
        if name == "extension":
            return self._extension
        if name == "magic":
            if self._magic is None:
                raise ValueError("MagicDetector not available")
            return self._magic
        raise ValueError(f"Unknown detector: {name}")


_default_registry: DetectorRegistry | None = None


def get_default_registry() -> DetectorRegistry:
    """Get or create the singleton DetectorRegistry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = DetectorRegistry()
    return _default_registry
