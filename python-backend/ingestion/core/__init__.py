"""Core types, exceptions, and config for the ingestion pipeline."""

from ingestion.core.config import IngestionConfig, get_config
from ingestion.core.exceptions import (
    ChunkingError,
    EmbeddingError,
    ExtractionError,
    IngestionError,
    NormalizationError,
    SinkError,
)
from ingestion.core.types import (
    ExtractedAlgorithm,
    ExtractedChunk,
    ExtractedCodeBlock,
    ExtractedDocument,
    ExtractedFigure,
    ExtractedFormula,
    ExtractedTable,
    Job,
    JobStatus,
    PipelineKind,
)

__all__ = [
    "ChunkingError",
    "EmbeddingError",
    "ExtractedAlgorithm",
    "ExtractedChunk",
    "ExtractedCodeBlock",
    "ExtractedDocument",
    "ExtractedFigure",
    "ExtractedFormula",
    "ExtractedTable",
    "ExtractionError",
    "IngestionConfig",
    "IngestionError",
    "Job",
    "JobStatus",
    "NormalizationError",
    "PipelineKind",
    "SinkError",
    "get_config",
]
