"""Extractor registry — auto-select by mime type or name.

In-process extractors (lightweight, in ingestion venv):
    pymupdf4llm, markdown, html, csv, code, note

Remote extractors (heavy, in extraction_layout venv via HTTP, Phase 2):
    docling, marker, mineru
"""

from __future__ import annotations

import os

from ingestion.extractors.base import DocumentExtractor
from ingestion.extractors.code_ext import CodeExtractor
from ingestion.extractors.csv_ext import CSVExtractor
from ingestion.extractors.html_ext import HTMLExtractor
from ingestion.extractors.markdown_ext import MarkdownExtractor
from ingestion.extractors.note_ext import NoteExtractor
from ingestion.extractors.pymupdf_ext import PyMuPDF4LLMExtractor
from ingestion.extractors.remote import (
    DoclingExtractor,
    MarkerExtractor,
    MineruExtractor,
)
from loguru import logger

# MIME → preferred extractor name (lookup is overridable via env)
_MIME_MAP: dict[str, str] = {
    "application/pdf": "pymupdf4llm",
    "text/markdown": "markdown",
    "text/html": "html",
    "text/csv": "csv",
    "text/tab-separated-values": "csv",
    "text/plain": "note",
    "text/x-python": "code",
    "text/x-rust": "code",
    "text/x-go": "code",
    "text/x-typescript": "code",
    "text/javascript": "code",
}


class ExtractorRegistry:
    """Map mime types and names to extractor instances."""

    def __init__(self) -> None:
        # In-process extractors (always loaded)
        self._by_name: dict[str, DocumentExtractor] = {
            "pymupdf4llm": PyMuPDF4LLMExtractor(),
            "markdown": MarkdownExtractor(),
            "html": HTMLExtractor(),
            "csv": CSVExtractor(),
            "note": NoteExtractor(),
            "code": CodeExtractor(),
            # Remote extractors (HTTP proxy to extraction_layout venv, Phase 2 stubs)
            "docling": DoclingExtractor(),
            "marker": MarkerExtractor(),
            "mineru": MineruExtractor(),
        }

        # Allow env override of PDF extractor (e.g. PDF_EXTRACTOR=docling once Phase 2)
        self._pdf_pref = os.environ.get("PDF_EXTRACTOR", "pymupdf4llm")
        if self._pdf_pref != "pymupdf4llm":
            logger.info("PDF extractor override: {}", self._pdf_pref)
            _MIME_MAP["application/pdf"] = self._pdf_pref

    def get(self, name: str) -> DocumentExtractor:
        if name not in self._by_name:
            raise ValueError(f"Unknown extractor: {name}")
        return self._by_name[name]

    def get_for_mime(self, mime_type: str) -> DocumentExtractor:
        from ingestion.core.exceptions import ExtractionError

        name = _MIME_MAP.get(mime_type)
        if name is not None:
            return self._by_name[name]

        # Fallback: any text/* mime → note (passthrough). Silent — this is expected.
        if mime_type.startswith("text/"):
            return self._by_name["note"]

        # Unknown BINARY mime → refuse rather than silently producing garbage.
        # Caller (pipeline) catches this as ExtractionError → job fails with clear msg.
        raise ExtractionError(
            f"No extractor for mime type '{mime_type}'. "
            "Add it to ingestion/extractors/registry.py:_MIME_MAP, or register "
            "a custom extractor in extractors/."
        )

    def available(self) -> list[str]:
        """List of locally available (in-process) extractors that can run right now."""
        return [name for name, ext in self._by_name.items() if ext.is_available()]
