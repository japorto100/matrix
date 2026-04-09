"""Core dataclasses for the ingestion pipeline.

Adopted from paperwatcher/paperwatcher/core/doc_extractor/base.py (1:1 copy with
JobStatus + Job + PipelineKind enums added on top).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import UUID, uuid4


# ─── Pipeline Job Tracking ──────────────────────────────────────────────────


class PipelineKind(str, Enum):
    """Which pipeline composer handled this job."""

    DOCUMENT = "document"
    NOTE = "note"
    LINK = "link"
    BATCH = "batch"


class JobStatus(str, Enum):
    """Pipeline job lifecycle states."""

    PENDING = "pending"
    DETECTING = "detecting"
    LOADING = "loading"
    EXTRACTING = "extracting"
    NORMALIZING = "normalizing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    DONE = "done"
    FAILED = "failed"
    SKIPPED_DEDUP = "skipped_dedup"


@dataclass
class Job:
    """Persistent job record (mirrors `ingestion.jobs` table)."""

    id: UUID = field(default_factory=uuid4)
    file_id: UUID | None = None
    pipeline: PipelineKind = PipelineKind.DOCUMENT
    user_id: str = "local"
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    chunks_total: int | None = None
    chunks_done: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    document_hash: str | None = None
    metadata: dict = field(default_factory=dict)


# ─── Document Extraction Dataclasses (1:1 from paperwatcher) ────────────────


@dataclass
class ExtractedTable:
    """A table extracted from a document."""

    id: str
    page: int
    caption: str | None = None
    content_md: str = ""
    content_csv: str = ""
    content_html: str = ""
    bbox: tuple[float, ...] | None = None
    confidence: float | None = None


@dataclass
class ExtractedFigure:
    """A figure extracted from a document."""

    id: str
    page: int
    caption: str | None = None
    image_path: Path | None = None
    figure_type: str = "other"  # chart | diagram | photo | plot | other
    bbox: tuple[float, ...] | None = None
    confidence: float | None = None


@dataclass
class ExtractedFormula:
    """A mathematical formula extracted from a document."""

    id: str
    page: int
    latex: str = ""
    context: str = ""
    display: bool = True  # True=display math, False=inline


@dataclass
class ExtractedAlgorithm:
    """A pseudocode algorithm block extracted from a document."""

    id: str
    page: int
    name: str | None = None
    content: str = ""
    caption: str | None = None


@dataclass
class ExtractedCodeBlock:
    """A code listing extracted from a document."""

    id: str
    page: int
    language: str | None = None
    content: str = ""
    caption: str | None = None


@dataclass
class ExtractedChunk:
    """A pre-split, section-aware text chunk for RAG indexing."""

    id: str  # "chunk_001"
    text: str
    section: str = ""  # Section name (e.g. "Methods", "Results")
    page_start: int = 0
    page_end: int = 0
    token_count: int = 0
    chunk_type: str = "text"  # "text" | "table" | "figure_caption" | "code"
    confidence: float | None = None


@dataclass
class ExtractedDocument:
    """Full structured extraction result from a document.

    Contains the complete markdown, structured JSON, and all extracted
    multimodal artifacts (tables, figures, formulas, etc.).
    """

    doc_id: str
    source_path: Path
    extractor: str  # "pymupdf4llm" | "docling" | "marker" | "markdown" | ...
    content_md: str = ""
    content_json: dict = field(default_factory=dict)

    tables: list[ExtractedTable] = field(default_factory=list)
    figures: list[ExtractedFigure] = field(default_factory=list)
    formulas: list[ExtractedFormula] = field(default_factory=list)
    algorithms: list[ExtractedAlgorithm] = field(default_factory=list)
    code_blocks: list[ExtractedCodeBlock] = field(default_factory=list)
    chunks: list[ExtractedChunk] = field(default_factory=list)

    footnotes: list[dict] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)

    page_count: int = 0
    page_images: list[Path] = field(default_factory=list)  # per-page PNGs
    language: str | None = None
    parse_warnings: list[str] = field(default_factory=list)
    schema_version: str = "2.0"
    extraction_time_s: float = 0.0

    section_count: int = 0
    chunk_count: int = 0
