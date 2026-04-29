"""Optional Microsoft MarkItDown extractor."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from ingestion.core.exceptions import ExtractionError
from ingestion.extractors.base import DocumentExtractor, ExtractedDocument


class MarkItDownExtractor(DocumentExtractor):
    """Lightweight optional converter for Office/HTML/simple PDF sources."""

    name = "markitdown"
    requires_gpu = False
    requires_model_download = False
    model_size_mb = 0

    def is_available(self) -> bool:
        return importlib.util.find_spec("markitdown") is not None

    def extract(self, path: Path) -> ExtractedDocument:
        try:
            from markitdown import MarkItDown
        except ImportError as exc:
            raise ExtractionError(
                "markitdown is not installed. Install optional Microsoft "
                "MarkItDown support before selecting PDF_EXTRACTOR=markitdown."
            ) from exc

        try:
            result = MarkItDown().convert(str(path))
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError(f"markitdown extraction failed: {exc}") from exc

        content_md = str(
            getattr(result, "text_content", None)
            or getattr(result, "markdown", None)
            or ""
        )
        if not content_md.strip():
            raise ExtractionError("markitdown extraction returned empty markdown")

        return ExtractedDocument(
            doc_id="",
            source_path=path,
            extractor=self.name,
            content_md=content_md,
            content_json={
                "markdown": content_md,
                "converter": "microsoft-markitdown",
            },
            section_count=sum(
                1
                for line in content_md.splitlines()
                if line.lstrip().startswith("#")
            ),
        )
