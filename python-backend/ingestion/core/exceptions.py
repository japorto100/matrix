"""Exception hierarchy for the ingestion pipeline."""

from __future__ import annotations


class IngestionError(Exception):
    """Base exception for all ingestion errors."""


class DetectionError(IngestionError):
    """Failed to detect file type."""


class LoadError(IngestionError):
    """Failed to load file bytes from storage."""


class ExtractionError(IngestionError):
    """Failed to extract structured content from file."""


class NormalizationError(IngestionError):
    """Failed to normalize extracted document."""


class ChunkingError(IngestionError):
    """Failed to split document into chunks."""


class EmbeddingError(IngestionError):
    """Failed to embed chunks."""


class SinkError(IngestionError):
    """Failed to write to a sink (Hindsight, Vector, Storage, KG)."""


class DedupSkip(IngestionError):
    """Document already exists (sha256 match) — not an error, just signaled."""

    def __init__(self, document_hash: str, existing_job_id: str):
        super().__init__(f"Duplicate document: {document_hash} (job {existing_job_id})")
        self.document_hash = document_hash
        self.existing_job_id = existing_job_id
