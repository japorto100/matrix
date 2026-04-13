"""File type detection (Phase 1).

Detects MIME type and extension from file path or bytes.
"""

from ingestion.detectors.base import DetectionResult, Detector
from ingestion.detectors.extension import ExtensionDetector
from ingestion.detectors.magic import MagicDetector
from ingestion.detectors.registry import DetectorRegistry

__all__ = [
    "DetectionResult",
    "Detector",
    "DetectorRegistry",
    "ExtensionDetector",
    "MagicDetector",
]
