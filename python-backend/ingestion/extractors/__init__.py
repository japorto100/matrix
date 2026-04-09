"""Document extractors (Phase 3 of pipeline).

In-process: pymupdf4llm + markdown/html/csv/code/note (adopted from paperwatcher).
Remote (HTTP to extraction_layout, Phase 2): docling, marker, mineru.
"""

from ingestion.extractors.base import DocumentExtractor
from ingestion.extractors.code_ext import CodeExtractor
from ingestion.extractors.csv_ext import CSVExtractor
from ingestion.extractors.html_ext import HTMLExtractor
from ingestion.extractors.markdown_ext import MarkdownExtractor
from ingestion.extractors.note_ext import NoteExtractor
from ingestion.extractors.pymupdf_ext import PyMuPDF4LLMExtractor
from ingestion.extractors.registry import ExtractorRegistry
from ingestion.extractors.remote import (
    DoclingExtractor,
    MarkerExtractor,
    MineruExtractor,
    RemoteLayoutExtractor,
)

__all__ = [
    "CSVExtractor",
    "CodeExtractor",
    "DocumentExtractor",
    "DoclingExtractor",
    "ExtractorRegistry",
    "HTMLExtractor",
    "MarkdownExtractor",
    "MarkerExtractor",
    "MineruExtractor",
    "NoteExtractor",
    "PyMuPDF4LLMExtractor",
    "RemoteLayoutExtractor",
]
