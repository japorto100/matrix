"""Note extractor — passthrough for raw text from AddMemoryModal Note tab.

This extractor is used by the NotePipeline composer. The "file" is just the
raw note text (no real file involved). The pipeline calls extract() with a
synthetic Path containing the note bytes.
"""

from __future__ import annotations

from pathlib import Path

from ingestion.extractors.base import DocumentExtractor, ExtractedDocument


class NoteExtractor(DocumentExtractor):
    """Passthrough extractor for plain text notes."""

    name = "note"

    def is_available(self) -> bool:
        return True

    def extract(self, path: Path) -> ExtractedDocument:
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        return ExtractedDocument(
            doc_id="",
            source_path=path,
            extractor=self.name,
            content_md=text,
            content_json={"text": text},
        )

    def extract_from_text(self, text: str) -> ExtractedDocument:
        """Extract directly from a string (no file needed)."""
        return ExtractedDocument(
            doc_id="",
            source_path=Path("note://inline"),
            extractor=self.name,
            content_md=text,
            content_json={"text": text},
        )
