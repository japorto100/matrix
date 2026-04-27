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
from ingestion.loaders.registry import LoaderRegistry
from ingestion.normalizers.markdown_cleaner import MarkdownCleaner
from ingestion.pipelines.document import DocumentPipeline
from ingestion.sinks.base import Sink, SinkResult


class FakeTracker:
    def __init__(self) -> None:
        self.saved_doc_id: str | None = None
        self.saved_chunks: list[tuple[str, str, str | None]] = []

    def start(
        self,
        *,
        pipeline,
        user_id: str,
        file_id: UUID | None,
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


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, **event: object) -> None:
        self.events.append(event)


class CaptureSink(Sink):
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


class FakeSinks:
    def __init__(self, sink: CaptureSink) -> None:
        self.sink = sink

    def has(self, name: str) -> bool:
        return name == self.sink.name

    def get(self, name: str) -> Sink:
        if name != self.sink.name:
            raise ValueError(name)
        return self.sink


@pytest.mark.asyncio
async def test_run_local_path_ingests_markdown_without_storage_services(tmp_path) -> None:
    source = tmp_path / "paper.md"
    source.write_text(
        "# GraphRAG Notes\n\nAgentic search narrows the gap.\n\n## Method\n\nUse retrieval gates.",
        encoding="utf-8",
    )
    tracker = FakeTracker()
    audit = FakeAudit()
    sink = CaptureSink()
    ctx = SimpleNamespace(
        config=SimpleNamespace(chunker_name="token", embedder_provider="deterministic"),
        detectors=DetectorRegistry(),
        loaders=LoaderRegistry(),
        extractors=ExtractorRegistry(),
        normalizer=MarkdownCleaner(),
        chunkers=ChunkerRegistry(chunk_size=20, chunk_overlap=2),
        embedders=EmbedderRegistry(),
        sinks=FakeSinks(sink),
        tracker=tracker,
        audit=audit,
        hasher=SimpleNamespace(hash_bytes=lambda data: "doc-hash"),
    )

    job = await DocumentPipeline(ctx).run_local_path(
        source,
        user_id="meta-harness",
        tags=["paper", "rag"],
        sinks_active=["capture"],
    )

    assert job.status == JobStatus.DONE
    assert job.file_id is not None
    assert job.metadata["source"] == "local"
    assert job.metadata["source_path"] == str(source.resolve())
    assert sink.doc is not None
    assert sink.doc.doc_id == str(job.file_id)
    assert len(sink.chunks) >= 1
    assert len(sink.embeddings) == len(sink.chunks)
    assert tracker.saved_doc_id == str(job.file_id)
    assert len(tracker.saved_chunks) == len(sink.chunks)
    assert audit.events[-1]["action"] == "INGESTION_LOCAL_FILE"
