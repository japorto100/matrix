"""Note Pipeline — raw text from AddMemoryModal Note tab → Hindsight.

Skips detect/load/extract/normalize phases — text is already clean.
"""

from __future__ import annotations

from ingestion.core.exceptions import DedupSkipError, IngestionError
from ingestion.core.types import Job, JobStatus, PipelineKind
from ingestion.extractors.note_ext import NoteExtractor
from ingestion.pipelines.base import Pipeline
from loguru import logger


class NotePipeline(Pipeline):
    """Inline text → chunk → embed → Hindsight (5 sec budget)."""

    name = "note"

    async def run(  # type: ignore[override]
        self,
        text: str,
        user_id: str = "local",
        tags: list[str] | None = None,
        title: str | None = None,
    ) -> Job:
        ctx = self.ctx
        job = ctx.tracker.start(
            pipeline=PipelineKind.NOTE,
            user_id=user_id,
            file_id=None,
            metadata={"tags": tags or [], "title": title, "sinks": ["hindsight"]},
        )

        try:
            # Dedup
            doc_hash = ctx.hasher.hash_text(text)
            existing = ctx.tracker.find_by_hash(doc_hash)
            if existing is not None:
                ctx.audit.emit(
                    action="INGESTION_DEDUP",
                    user_id=user_id,
                    target_type="note",
                    target_id=str(job.id),
                    metadata={
                        "document_hash": doc_hash,
                        "existing_job_id": str(existing["id"]),
                    },
                )
                ctx.tracker.update(
                    job, status=JobStatus.SKIPPED_DEDUP, document_hash=doc_hash
                )
                ctx.tracker.complete(job)
                raise DedupSkipError(doc_hash, str(existing["id"]))
            ctx.tracker.update(job, document_hash=doc_hash)

            # Phase 3 (inline): NoteExtractor passthrough
            ctx.tracker.update(job, status=JobStatus.EXTRACTING)
            note_extractor = NoteExtractor()
            doc = note_extractor.extract_from_text(text)
            doc.doc_id = f"note_{job.id}"

            # Phase 5: chunk
            ctx.tracker.update(job, status=JobStatus.CHUNKING)
            chunker = ctx.chunkers.get(ctx.config.chunker_name)
            chunks = chunker.chunk(doc)
            ctx.tracker.update(
                job, chunks_total=len(chunks), status=JobStatus.EMBEDDING
            )
            logger.info("note {} → {} chunks", job.id, len(chunks))

            if not chunks:
                ctx.tracker.complete(job)
                return job

            # Phase 6: embed
            embedder = ctx.embedders.get(ctx.config.embedder_provider)
            embeddings = embedder.embed([c.text for c in chunks])

            # Phase 7: sinks (Hindsight only for notes)
            ctx.tracker.update(job, status=JobStatus.STORING)
            sink = ctx.sinks.get("hindsight")
            await sink.write_batch(doc, chunks, embeddings, job)

            ctx.tracker.update(job, chunks_done=len(chunks))
            ctx.tracker.complete(job)
            ctx.audit.emit(
                action="INGESTION_NOTE",
                user_id=user_id,
                target_type="note",
                target_id=str(job.id),
                metadata={"chunks": len(chunks), "title": title},
            )
            return job

        except DedupSkipError:
            raise
        except Exception as e:  # noqa: BLE001
            ctx.tracker.fail(job, str(e))
            raise IngestionError(f"note pipeline failed: {e}") from e
