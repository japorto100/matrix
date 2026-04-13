"""Storage sink — updates artifact metadata in Go gateway after ingestion.

The bytes are already in SeaweedFS (uploaded by the frontend BFF before this
worker is called). This sink just patches the metadata to mark ingestion as
complete and record chunk count + extractor used.
"""

from __future__ import annotations

from ingestion.clients.go_storage import GoStorageClient
from ingestion.core.types import ExtractedChunk, ExtractedDocument, Job
from ingestion.sinks.base import Sink, SinkResult
from loguru import logger


class StorageSink(Sink):
    """Update artifact metadata in Go gateway with ingestion results."""

    name = "storage"

    def __init__(self, client: GoStorageClient) -> None:
        self.client = client

    async def write_batch(
        self,
        doc: ExtractedDocument,
        chunks: list[ExtractedChunk],
        embeddings: list[list[float]],
        job: Job,
    ) -> SinkResult:
        if not job.file_id:
            return SinkResult(sink_name=self.name, skipped=len(chunks))

        patch = {
            "ingestion_status": "indexed",
            "ingestion_job_id": str(job.id),
            "extractor": doc.extractor,
            "chunk_count": len(chunks),
            "page_count": doc.page_count,
        }
        try:
            await self.client.patch_metadata(job.file_id, patch)
        except Exception as e:  # noqa: BLE001
            logger.warning("StorageSink patch_metadata failed: {}", e)
            return SinkResult(sink_name=self.name, failed=1)

        return SinkResult(
            sink_name=self.name,
            written=1,
            metadata={"file_id": str(job.file_id)},
        )
