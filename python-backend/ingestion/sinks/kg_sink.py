"""KG Pipeline sink — forwards chunks to kg_pipeline worker for entity extraction.

In Phase 1 the kg_pipeline worker is a stub. The KGPipelineClient returns
{"skipped": True} and this sink writes nothing.
In Phase 2 (when KG_PIPELINE_ENABLED=true) it forwards each chunk's text to
the kg-pipeline-worker on Port 8099 which extracts entities + relations and
writes them to Kuzu.
"""

from __future__ import annotations

from ingestion.clients.kg_pipeline import KGPipelineClient
from ingestion.core.types import ExtractedChunk, ExtractedDocument, Job
from ingestion.sinks.base import Sink, SinkResult
from loguru import logger


class KGSink(Sink):
    """Forward chunks to kg_pipeline worker for entity/relation extraction."""

    name = "kg"

    def __init__(self, client: KGPipelineClient) -> None:
        self.client = client

    async def write_batch(
        self,
        doc: ExtractedDocument,
        chunks: list[ExtractedChunk],
        embeddings: list[list[float]],
        job: Job,
    ) -> SinkResult:
        if not self.client.enabled:
            return SinkResult(
                sink_name=self.name,
                skipped=len(chunks),
                metadata={"reason": "kg_pipeline disabled"},
            )

        written = 0
        skipped = 0
        for chunk in chunks:
            result = await self.client.extract(chunk.text, doc.doc_id)
            if result.get("skipped"):
                skipped += 1
            else:
                written += len(result.get("entities", [])) + len(result.get("relations", []))

        logger.info("KGSink processed {} chunks (skipped={})", len(chunks), skipped)
        return SinkResult(
            sink_name=self.name,
            written=written,
            skipped=skipped,
        )
