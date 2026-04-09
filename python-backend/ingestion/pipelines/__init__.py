"""Pipeline composers (verdrahten die Phasen)."""

from ingestion.pipelines.base import Pipeline, PipelineContext
from ingestion.pipelines.document import DocumentPipeline
from ingestion.pipelines.link import LinkPipeline
from ingestion.pipelines.note import NotePipeline

__all__ = [
    "DocumentPipeline",
    "LinkPipeline",
    "NotePipeline",
    "Pipeline",
    "PipelineContext",
]
