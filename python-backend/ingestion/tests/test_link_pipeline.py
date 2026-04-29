from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from ingestion.chunkers.registry import ChunkerRegistry
from ingestion.core.types import ExtractedChunk, ExtractedDocument, Job, JobStatus
from ingestion.detectors.registry import DetectorRegistry
from ingestion.embedders.registry import EmbedderRegistry
from ingestion.extractors.registry import ExtractorRegistry
from ingestion.loaders.base import LoadResult
from ingestion.normalizers.markdown_cleaner import MarkdownCleaner
from ingestion.pipelines.link import LinkPipeline
from ingestion.sinks.base import Sink, SinkResult


class _Tracker:
    def __init__(self) -> None:
        self.saved_doc_id: str | None = None
        self.saved_chunks: list[tuple[str, str, str | None]] = []

    def start(
        self,
        *,
        pipeline,
        user_id: str,
        file_id: UUID | None = None,
        metadata: dict,
        document_hash: str | None = None,
    ) -> Job:
        return Job(
            pipeline=pipeline,
            user_id=user_id,
            file_id=file_id,
            metadata=metadata,
            document_hash=document_hash,
            started_at=datetime.now(UTC),
        )

    def update(self, job: Job, **fields: object) -> None:
        for key, value in fields.items():
            setattr(job, key, value)

    def find_by_hash(self, document_hash: str) -> dict | None:
        return None

    def complete(self, job: Job) -> None:
        job.status = JobStatus.DONE
        job.completed_at = datetime.now(UTC)
        job.progress = 1.0

    def fail(self, job: Job, error: str) -> None:
        job.status = JobStatus.FAILED
        job.error_message = error

    def delete_chunk_hashes_by_doc(self, doc_id: str) -> int:
        self.saved_doc_id = doc_id
        self.saved_chunks = []
        return 0

    def save_chunk_hashes(
        self,
        job_id: UUID,
        doc_id: str,
        chunks_with_hashes: list[tuple[str, str, str | None]],
    ) -> None:
        self.saved_doc_id = doc_id
        self.saved_chunks = chunks_with_hashes


class _Audit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, **event: object) -> None:
        self.events.append(event)


class _SourceArtifacts:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def upsert(self, **row: object) -> dict:
        self.rows.append(row)
        return row


class _HttpLoader:
    async def load(self, identifier: str) -> LoadResult:
        return LoadResult(
            data=b"# URL Paper\n\nAgentic search narrows the gap.",
            filename="paper.md",
            source="http",
            content_type="text/markdown",
            size=42,
        )


class _Loaders:
    def get(self, name: str) -> _HttpLoader:
        assert name == "http"
        return _HttpLoader()


class _Sink(Sink):
    name = "capture"

    def __init__(self) -> None:
        self.doc: ExtractedDocument | None = None
        self.chunks: list[ExtractedChunk] = []
        self.embeddings: list[list[float]] = []

    async def write_batch(
        self,
        doc: ExtractedDocument,
        chunks: list[ExtractedChunk],
        embeddings: list[list[float]],
        job: Job,
    ) -> SinkResult:
        self.doc = doc
        self.chunks = chunks
        self.embeddings = embeddings
        return SinkResult(sink_name=self.name, written=len(chunks))


class _Sinks:
    def __init__(self, sink: _Sink) -> None:
        self.sink = sink

    def has(self, name: str) -> bool:
        return name == self.sink.name

    def get(self, name: str) -> Sink:
        if name != self.sink.name:
            raise ValueError(name)
        return self.sink


@pytest.mark.asyncio
async def test_link_pipeline_persists_source_artifact_and_citations() -> None:
    url = "https://arxiv.org/pdf/2604.09666"
    tracker = _Tracker()
    audit = _Audit()
    source_artifacts = _SourceArtifacts()
    sink = _Sink()
    ctx = SimpleNamespace(
        config=SimpleNamespace(
            chunker_name="token",
            embedder_provider="deterministic",
            embedder_model="deterministic-test",
        ),
        detectors=DetectorRegistry(),
        loaders=_Loaders(),
        extractors=ExtractorRegistry(),
        normalizer=MarkdownCleaner(),
        chunkers=ChunkerRegistry(chunk_size=20, chunk_overlap=2),
        embedders=EmbedderRegistry(),
        sinks=_Sinks(sink),
        tracker=tracker,
        source_artifacts=source_artifacts,
        audit=audit,
        hasher=SimpleNamespace(hash_bytes=lambda data: "url-doc-hash"),
    )

    job = await LinkPipeline(ctx).run(
        url,
        user_id="meta-harness",
        tags=["paper", "url"],
        title="GraphRAG benchmark",
        sinks_active=["capture"],
    )

    assert job.status == JobStatus.DONE
    assert job.file_id is not None
    assert job.metadata["source"] == "url"
    assert job.metadata["url"] == url
    assert sink.doc is not None
    assert sink.doc.doc_id == f"link_{job.id}"
    assert len(sink.chunks) >= 1
    first_meta = job.metadata["chunk_metadata"][sink.chunks[0].id]
    assert first_meta["source_artifact_id"] == str(job.file_id)
    assert first_meta["source_uri"] == url
    assert first_meta["citation_ref"].startswith(f"{url}#chunk={sink.chunks[0].id}")
    assert source_artifacts.rows[0]["source_artifact_id"] == job.file_id
    assert source_artifacts.rows[0]["source_uri"] == url
    assert source_artifacts.rows[0]["content_hash"] == "url-doc-hash"
    assert source_artifacts.rows[0]["metadata"]["source_artifact_id"] == str(
        job.file_id
    )
    assert tracker.saved_doc_id == str(job.file_id)
    assert len(tracker.saved_chunks) == len(sink.chunks)
    assert audit.events[-1]["action"] == "INGESTION_LINK"
