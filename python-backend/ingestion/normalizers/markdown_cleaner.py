"""Markdown cleaner — remove headers/footers/page numbers/excessive whitespace."""

from __future__ import annotations

import re

from ingestion.core.types import ExtractedDocument
from ingestion.normalizers.base import Normalizer

# Patterns for typical PDF noise after pymupdf4llm conversion
_PAGE_NUMBER_RE = re.compile(r"^\s*-?\s*\d+\s*-?\s*$", re.MULTILINE)
_PAGE_HEADER_RE = re.compile(r"^Page \d+ of \d+\s*$", re.MULTILINE | re.IGNORECASE)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_TRAILING_WS_RE = re.compile(r"[ \t]+$", re.MULTILINE)


class MarkdownCleaner(Normalizer):
    """Strip typical PDF artifacts from converted markdown."""

    name = "markdown_cleaner"

    def normalize(self, doc: ExtractedDocument) -> ExtractedDocument:
        text = doc.content_md
        text = _PAGE_NUMBER_RE.sub("", text)
        text = _PAGE_HEADER_RE.sub("", text)
        text = _TRAILING_WS_RE.sub("", text)
        text = _MULTI_BLANK_RE.sub("\n\n", text)
        text = text.strip()
        doc.content_md = text
        if "markdown" in doc.content_json:
            doc.content_json["markdown"] = text
        return doc
