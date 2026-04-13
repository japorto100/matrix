"""Extension-based file type detector (fast, no I/O)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from ingestion.core.exceptions import DetectionError
from ingestion.detectors.base import DetectionResult, Detector

# Custom mime mappings beyond mimetypes stdlib
_CUSTOM_MIMES: dict[str, str] = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".jsonl": "application/x-jsonlines",
    ".py": "text/x-python",
    ".rs": "text/x-rust",
    ".go": "text/x-go",
    ".ts": "text/x-typescript",
    ".tsx": "text/x-typescript",
    ".js": "text/javascript",
    ".jsx": "text/javascript",
}


class ExtensionDetector(Detector):
    """Detect file type by extension only.

    Fastest path — no file I/O. Use this when filename is trusted.
    """

    name = "extension"

    def detect(
        self,
        path: Path | None = None,
        data: bytes | None = None,
        filename: str | None = None,
    ) -> DetectionResult:
        if path is not None:
            ext = path.suffix.lower()
            name_for_mime = path.name
        elif filename is not None:
            ext = Path(filename).suffix.lower()
            name_for_mime = filename
        else:
            raise DetectionError("ExtensionDetector requires path or filename")

        if not ext:
            raise DetectionError(f"No extension on filename: {name_for_mime}")

        if ext in _CUSTOM_MIMES:
            return DetectionResult(mime_type=_CUSTOM_MIMES[ext], extension=ext)

        mime, _ = mimetypes.guess_type(name_for_mime)
        if mime:
            return DetectionResult(mime_type=mime, extension=ext)

        return DetectionResult(mime_type="application/octet-stream", extension=ext, confidence=0.5)
