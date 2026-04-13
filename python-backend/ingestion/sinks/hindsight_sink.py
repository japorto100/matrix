"""Hindsight Memory Engine sink — writes chunks via retain_batch_async.

Uses hindsight-api-slim package directly. Same package version as the main
agent runtime, sharing the same Postgres backend (HINDSIGHT_DB_URL).

Note (07.04.2026): Hindsight computes embeddings INTERNALLY via its own
EmbeddingProvider — we do NOT pass our own embeddings here. Our pipeline's
embedder phase is only used by vector_sink (Phase 2 direct ChromaDB) and
kg_sink (no embeddings needed). For Hindsight-only ingestion, the embedder
phase could be skipped — but we keep it because most pipelines want at
least one of {vector, kg} sinks alongside hindsight.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from ingestion.core.exceptions import SinkError
from ingestion.core.types import ExtractedChunk, ExtractedDocument, Job
from ingestion.sinks.base import Sink, SinkResult
from loguru import logger


class HindsightSink(Sink):
    """Persist chunks to Hindsight via retain_batch_async (per-user bank)."""

    name = "hindsight"

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or os.environ.get("HINDSIGHT_DB_URL")
        self._engine: Any = None
        self._initialized = False
        self._closed = False

    async def open(self) -> None:
        if self._initialized:
            return
        if not self.db_url:
            raise SinkError("HINDSIGHT_DB_URL not set — cannot init Hindsight sink")
        try:
            from hindsight_api.engine.memory_engine import MemoryEngine
        except ImportError as e:
            raise SinkError("hindsight-api-slim not installed in ingestion venv") from e

        # SyncTaskBackend = inline consolidation (no separate worker process)
        try:
            from hindsight_api.engine.task_backend import SyncTaskBackend

            task_backend = SyncTaskBackend()
        except Exception:
            task_backend = None

        self._engine = MemoryEngine(db_url=self.db_url, task_backend=task_backend)
        await self._engine.initialize()
        self._initialized = True
        logger.info("HindsightSink initialized")

    async def close(self) -> None:
        if self._closed or self._engine is None:
            return
        self._closed = True
        if hasattr(self._engine, "close"):
            try:
                await self._engine.close()
                logger.info("HindsightSink closed")
            except Exception as e:  # noqa: BLE001
                logger.warning("HindsightSink close: {}", e)

    async def write_batch(
        self,
        doc: ExtractedDocument,
        chunks: list[ExtractedChunk],
        embeddings: list[list[float]],
        job: Job,
    ) -> SinkResult:
        """Write chunks to Hindsight via retain_batch_async.

        Note: `embeddings` is ignored — Hindsight embeds internally.
        """
        await self.open()
        if self._engine is None:
            raise SinkError("HindsightSink not initialized")

        try:
            from hindsight_api.models import RequestContext
        except ImportError as e:
            raise SinkError("hindsight_api.models.RequestContext not importable") from e

        bank_id = f"user_{job.user_id}"
        job_tags: list[str] = list((job.metadata or {}).get("tags", []))
        now = datetime.now(UTC)

        contents: list[dict[str, Any]] = []
        for chunk in chunks:
            chunk_tags = list(job_tags)
            chunk_tags.append(f"doc:{doc.doc_id}")
            chunk_tags.append(f"extractor:{doc.extractor}")
            if chunk.section:
                chunk_tags.append(f"section:{chunk.section}")

            metadata: dict[str, Any] = {
                "doc_id": doc.doc_id,
                "chunk_id": chunk.id,
                "section": chunk.section,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "token_count": chunk.token_count,
                "extractor": doc.extractor,
                "ingestion_job_id": str(job.id),
                "pipeline": job.pipeline.value,
            }
            if doc.source_path:
                metadata["source_path"] = str(doc.source_path)
            if job.file_id:
                metadata["file_id"] = str(job.file_id)

            contents.append(
                {
                    "content": chunk.text,
                    "context": (
                        f"doc:{doc.doc_id} section:{chunk.section or 'untitled'} chunk:{chunk.id}"
                    ),
                    "event_date": now,
                    "tags": chunk_tags,
                    "metadata": metadata,
                    "document_id": f"{doc.doc_id}:{chunk.id}",
                }
            )

        try:
            unit_ids = await self._engine.retain_batch_async(
                bank_id=bank_id,
                contents=contents,
                request_context=RequestContext(),
                document_tags=job_tags,
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("HindsightSink retain_batch_async failed")
            return SinkResult(
                sink_name=self.name,
                failed=len(contents),
                metadata={"error": str(e)},
            )

        # unit_ids is list[list[ID]] — count total facts retained
        facts_total = sum(len(ids) for ids in (unit_ids or []))
        logger.info(
            "HindsightSink wrote {} chunks → {} facts to bank {}",
            len(contents),
            facts_total,
            bank_id,
        )

        return SinkResult(
            sink_name=self.name,
            written=len(contents),
            metadata={"bank_id": bank_id, "facts_total": facts_total},
        )

    async def delete_by_hashes(self, content_hashes: set[str]) -> int:
        """Delete memory units whose chunks have the given content hashes.

        Used by smart_reindex() to remove chunks that no longer exist after
        a document edit. Phase 1 implementation: query Postgres directly via
        the same connection Hindsight uses (HINDSIGHT_DB_URL).

        Hindsight stores `content_hash` on its chunks table, NOT on memory_units.
        We match memory_units → chunks via chunks.memory_unit_id and delete the
        memory_units whose chunks all match.
        """
        if not content_hashes:
            return 0
        if not self.db_url:
            return 0

        try:
            import psycopg
        except ImportError:
            return 0

        try:
            with psycopg.connect(self.db_url, autocommit=True) as conn:
                # Best-effort: try the chunks table first (newer Hindsight schema)
                try:
                    cur = conn.execute(
                        """
                        DELETE FROM hindsight.memory_units
                        WHERE id IN (
                            SELECT memory_unit_id FROM hindsight.chunks
                            WHERE content_hash = ANY(%s)
                        )
                        """,
                        (list(content_hashes),),
                    )
                    return cur.rowcount or 0
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "delete_by_hashes via chunks table failed (schema differs?): {}", e
                    )
                    return 0
        except Exception as e:  # noqa: BLE001
            logger.warning("delete_by_hashes connect failed: {}", e)
            return 0
