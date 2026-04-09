"""Markdown file extractor — passthrough with section counting."""

from __future__ import annotations

import re
from pathlib import Path

from ingestion.extractors.base import DocumentExtractor, ExtractedDocument


class MarkdownExtractor(DocumentExtractor):
    """Trivial extractor for .md / .markdown files."""

    name = "markdown"

    def is_available(self) -> bool:
        return True

    def extract(self, path: Path) -> ExtractedDocument:
        text = path.read_text(encoding="utf-8", errors="replace")
        sections = len(re.findall(r"^#{1,6}\s+", text, re.MULTILINE))
        return ExtractedDocument(
            doc_id="",
            source_path=path,
            extractor=self.name,
            content_md=text,
            content_json={"markdown": text},
            section_count=sections,
        )
