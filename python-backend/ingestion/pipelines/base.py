"""Pipeline ABC + shared composition context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ingestion.chunkers.registry import ChunkerRegistry
from ingestion.clients.go_storage import GoStorageClient
from ingestion.clients.kg_pipeline import KGPipelineClient
from ingestion.core.config import IngestionConfig
from ingestion.core.types import Job
from ingestion.detectors.registry import DetectorRegistry
from ingestion.embedders.registry import EmbedderRegistry
from ingestion.extractors.registry import ExtractorRegistry
from ingestion.loaders.registry import LoaderRegistry
from ingestion.normalizers.markdown_cleaner import MarkdownCleaner
from ingestion.sinks.registry import SinkRegistry
from ingestion.tracking.artifacts import SourceArtifactRegistry
from ingestion.tracking.audit import AuditEmitter
from ingestion.tracking.dedup import DocumentHasher
from ingestion.tracking.jobs import JobTracker


@dataclass
class PipelineContext:
    """Shared dependencies passed to all pipelines.

    Constructed once at worker startup, reused across requests.
    """

    config: IngestionConfig
    detectors: DetectorRegistry
    loaders: LoaderRegistry
    extractors: ExtractorRegistry
    normalizer: MarkdownCleaner
    chunkers: ChunkerRegistry
    embedders: EmbedderRegistry
    sinks: SinkRegistry
    tracker: JobTracker
    source_artifacts: SourceArtifactRegistry
    audit: AuditEmitter
    hasher: DocumentHasher
    go_storage: GoStorageClient
    kg_client: KGPipelineClient

    @classmethod
    def from_config(cls, config: IngestionConfig) -> PipelineContext:
        go_storage = GoStorageClient(base_url=config.artifact_gateway_base_url)
        kg_client = KGPipelineClient(
            base_url=config.kg_pipeline_url,
            enabled=config.kg_pipeline_enabled,
        )
        return cls(
            config=config,
            detectors=DetectorRegistry(),
            loaders=LoaderRegistry(go_storage_client=go_storage),
            extractors=ExtractorRegistry(),
            normalizer=MarkdownCleaner(),
            chunkers=ChunkerRegistry(
                chunk_size=config.chunker_size, chunk_overlap=config.chunker_overlap
            ),
            embedders=EmbedderRegistry(
                default_model=config.embedder_model,
                remote_base_url=config.embedder_base_url,
                remote_api_key=config.embedder_api_key,
            ),
            sinks=SinkRegistry(
                go_storage_client=go_storage,
                kg_client=kg_client,
                hindsight_db_url=config.db_url,
            ),
            tracker=JobTracker(db_url=config.db_url),
            source_artifacts=SourceArtifactRegistry(db_url=config.db_url),
            audit=AuditEmitter(db_url=config.db_url),
            hasher=DocumentHasher(),
            go_storage=go_storage,
            kg_client=kg_client,
        )


class Pipeline(ABC):
    """Abstract base for all ingestion pipelines."""

    name: str = ""

    def __init__(self, ctx: PipelineContext) -> None:
        self.ctx = ctx

    @abstractmethod
    async def run(self, **kwargs: object) -> Job:
        """Run the full pipeline. Returns the completed Job."""
