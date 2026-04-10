"""Link Pipeline — URL → fetch HTML → extract → chunk → Hindsight."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from ingestion.core.exceptions import DedupSkipError, IngestionError
from ingestion.core.types import Job, JobStatus, PipelineKind
from ingestion.pipelines.base import Pipeline


class LinkPipeline(Pipeline):
    """URL → HttpLoader → HTMLExtractor → chunk → embed → Hindsight."""

    name = "link"

    async def run(  # type: ignore[override]
        self,
        url: str,
        user_id: str = "local",
        tags: list[str] | None = None,
        title: str | None = None,
    ) -> Job:
        ctx = self.ctx
        job = ctx.tracker.start(
            pipeline=PipelineKind.LINK,
            user_id=user_id,
            metadata={
                "tags": tags or [],
                "title": title,
                "url": url,
                "sinks": ["hindsight"],
            },
        )

        try:
            # Phase 2: load
            ctx.tracker.update(job, status=JobStatus.LOADING)
            loader = ctx.loaders.get("http")
            loaded = await loader.load(url)
            logger.info("fetched {} bytes from {}", loaded.size, url)

            # Dedup
            doc_hash = ctx.hasher.hash_bytes(loaded.data)
            existing = ctx.tracker.find_by_hash(doc_hash)
            if existing is not None:
                ctx.audit.emit(
                    action="INGESTION_DEDUP",
                    user_id=user_id,
                    target_type="link",
                    target_id=url,
                    metadata={"existing_job_id": existing["id"]},
                )
                ctx.tracker.update(
                    job, status=JobStatus.SKIPPED_DEDUP, document_hash=doc_hash
                )
                ctx.tracker.complete(job)
                raise DedupSkipError(doc_hash, existing["id"])
            ctx.tracker.update(job, document_hash=doc_hash)

            # Detect (likely text/html)
            detection = ctx.detectors.detect(data=loaded.data, filename=loaded.filename)

            # Phase 3: extract
            ctx.tracker.update(job, status=JobStatus.EXTRACTING)
            extractor = ctx.extractors.get_for_mime(detection.mime_type)
            tmp = self._materialize(loaded.data, loaded.filename)
            try:
                doc = extractor.extract_timed(tmp)
                doc.doc_id = f"link_{job.id}"
                doc.content_json["url"] = url
            finally:
                try:
                    tmp.unlink()
                except OSError:
                    pass

            # Phase 4: normalize
            ctx.tracker.update(job, status=JobStatus.NORMALIZING)
            doc = ctx.normalizer.normalize(doc)

            # Phase 5: chunk
            ctx.tracker.update(job, status=JobStatus.CHUNKING)
            chunker = ctx.chunkers.get(ctx.config.chunker_name)
            chunks = chunker.chunk(doc)
            ctx.tracker.update(
                job, chunks_total=len(chunks), status=JobStatus.EMBEDDING
            )

            if not chunks:
                ctx.tracker.complete(job)
                return job

            # Phase 6: embed
            embedder = ctx.embedders.get(ctx.config.embedder_provider)
            embeddings = embedder.embed([c.text for c in chunks])

            # Phase 7: sinks (Hindsight only)
            ctx.tracker.update(job, status=JobStatus.STORING)
            sink = ctx.sinks.get("hindsight")
            await sink.write_batch(doc, chunks, embeddings, job)

            ctx.tracker.update(job, chunks_done=len(chunks))
            ctx.tracker.complete(job)
            ctx.audit.emit(
                action="INGESTION_LINK",
                user_id=user_id,
                target_type="link",
                target_id=url,
                metadata={"chunks": len(chunks), "title": title},
            )
            return job

        except DedupSkipError:
            raise
        except Exception as e:  # noqa: BLE001
            ctx.tracker.fail(job, str(e))
            raise IngestionError(f"link pipeline failed: {e}") from e

    def _materialize(self, data: bytes, filename: str) -> Path:
        """Write bytes to a temp file (UUID-prefixed to avoid collisions)."""
        import tempfile
        from uuid import uuid4

        tmp_dir = Path(tempfile.gettempdir()) / "matrix-ingestion"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid4().hex}_{Path(filename).name}"
        tmp_path = tmp_dir / safe_name
        tmp_path.write_bytes(data)
        return tmp_path
