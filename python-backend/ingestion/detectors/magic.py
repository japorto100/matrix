"""libmagic-based file type detector (more reliable, requires bytes)."""

from __future__ import annotations

from pathlib import Path

from ingestion.core.exceptions import DetectionError
from ingestion.detectors.base import DetectionResult, Detector

try:
    import magic  # type: ignore[import-not-found]

    _MAGIC_AVAILABLE = True
except ImportError:
    _MAGIC_AVAILABLE = False


# Map common libmagic mime → extension
_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "text/markdown": ".md",
    "text/html": ".html",
    "text/csv": ".csv",
    "text/plain": ".txt",
    "application/json": ".json",
    "application/zip": ".zip",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


class MagicDetector(Detector):
    """Detect file type by inspecting magic bytes (libmagic)."""

    name = "magic"

    def __init__(self) -> None:
        if not _MAGIC_AVAILABLE:
            raise DetectionError(
                "python-magic is not installed. Install with: "
                "pip install python-magic-bin (Windows) or python-magic (Linux/Mac)"
            )
        self._magic = magic.Magic(mime=True)

    def detect(
        self,
        path: Path | None = None,
        data: bytes | None = None,
        filename: str | None = None,
    ) -> DetectionResult:
        if data is not None:
            mime = self._magic.from_buffer(data[:8192])
        elif path is not None:
            mime = self._magic.from_file(str(path))
        else:
            raise DetectionError("MagicDetector requires path or data")

        ext = _MIME_TO_EXT.get(mime, "")
        return DetectionResult(mime_type=mime, extension=ext, confidence=0.95)
