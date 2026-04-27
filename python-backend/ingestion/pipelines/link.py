"""Link Pipeline — URL → fetch HTML → extract → chunk → Hindsight."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from ingestion.core.exceptions import DedupSkipError, IngestionError
from ingestion.core.types import ExtractedChunk, ExtractedDocument, Job, JobStatus, PipelineKind
from ingestion.pipelines.base import Pipeline
from ingestion.tracking.dedup import DocumentHasher
from loguru import logger


class LinkPipeline(Pipeline):
    """URL → HttpLoader → HTMLExtractor → chunk → embed → Hindsight."""

    name = "link"

    async def run(  # type: ignore[override]
        self,
        url: str,
        user_id: str = "local",
        tags: list[str] | None = None,
        title: str | None = None,
        sinks_active: list[str] | None = None,
    ) -> Job:
        ctx = self.ctx
        sinks_active = sinks_active or ["hindsight"]
        source_artifact_id = uuid5(NAMESPACE_URL, url)
        job = ctx.tracker.start(
            pipeline=PipelineKind.LINK,
            user_id=user_id,
            file_id=source_artifact_id,
            metadata={
                "tags": tags or [],
                "title": title,
                "url": url,
                "sinks": sinks_active,
                "source": "url",
                "source_artifact_id": str(source_artifact_id),
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
                ctx.source_artifacts.upsert(
                    source_artifact_id=source_artifact_id,
                    source_uri=url,
                    source_kind="url",
                    fetch_method="http",
                    content_hash=doc_hash,
                    mime_type=loaded.content_type,
                    size_bytes=loaded.size,
                    parser_name=None,
                    parser_version=None,
                    chunker_name=ctx.config.chunker_name,
                    chunk_count=existing.get("chunks_total"),
                    embedding_provider=ctx.config.embedder_provider,
                    embedding_model=ctx.config.embedder_model,
                    embedding_dim=None,
                    metadata={
                        "job_id": str(job.id),
                        "dedup_existing_job_id": str(existing["id"]),
                        "url": url,
                        "title": title,
                        "tags": tags or [],
                        "sinks": sinks_active,
                    },
                )
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
            self._attach_source_metadata(
                job=job,
                doc=doc,
                chunks=chunks,
                source_artifact_id=source_artifact_id,
                source_uri=url,
                source_kind="url",
                fetch_method="http",
                content_hash=doc_hash,
                mime_type=detection.mime_type,
            )
            ctx.tracker.update(
                job, chunks_total=len(chunks), status=JobStatus.EMBEDDING
            )

            if not chunks:
                ctx.source_artifacts.upsert(
                    source_artifact_id=source_artifact_id,
                    source_uri=url,
                    source_kind="url",
                    fetch_method="http",
                    content_hash=doc_hash,
                    mime_type=detection.mime_type,
                    size_bytes=loaded.size,
                    parser_name=doc.extractor,
                    parser_version=doc.schema_version,
                    chunker_name=ctx.config.chunker_name,
                    chunk_count=0,
                    embedding_provider=ctx.config.embedder_provider,
                    embedding_model=ctx.config.embedder_model,
                    embedding_dim=None,
                    metadata=job.metadata.get("source_artifact", {}),
                )
                ctx.tracker.complete(job)
                return job

            # Phase 6: embed
            embedder = ctx.embedders.get(ctx.config.embedder_provider)
            embeddings = embedder.embed([c.text for c in chunks])

            # Phase 7: sinks (Hindsight only)
            embedding_dim = (
                len(embeddings[0]) if embeddings else getattr(embedder, "dim", None)
            )
            ctx.source_artifacts.upsert(
                source_artifact_id=source_artifact_id,
                source_uri=url,
                source_kind="url",
                fetch_method="http",
                content_hash=doc_hash,
                mime_type=detection.mime_type,
                size_bytes=loaded.size,
                parser_name=doc.extractor,
                parser_version=doc.schema_version,
                chunker_name=ctx.config.chunker_name,
                chunk_count=len(chunks),
                embedding_provider=ctx.config.embedder_provider,
                embedding_model=ctx.config.embedder_model,
                embedding_dim=embedding_dim,
                metadata={
                    **job.metadata.get("source_artifact", {}),
                    "job_id": str(job.id),
                    "url": url,
                    "title": title,
                    "tags": tags or [],
                    "sinks": sinks_active,
                },
            )
            ctx.tracker.update(job, status=JobStatus.STORING)
            for sink_name in sinks_active:
                if not ctx.sinks.has(sink_name):
                    logger.warning("sink {} not registered, skipping", sink_name)
                    continue
                sink = ctx.sinks.get(sink_name)
                result = await sink.write_batch(doc, chunks, embeddings, job)
                logger.info(
                    "sink {}: written={} skipped={} failed={}",
                    sink_name,
                    result.written,
                    result.skipped,
                    result.failed,
                )

            hashes_by_id = {c.id: DocumentHasher.hash_chunk(c) for c in chunks}
            ctx.tracker.delete_chunk_hashes_by_doc(str(source_artifact_id))
            ctx.tracker.save_chunk_hashes(
                job.id,
                str(source_artifact_id),
                [(c.id, hashes_by_id[c.id], c.section or None) for c in chunks],
            )

            ctx.tracker.update(job, chunks_done=len(chunks))
            ctx.tracker.complete(job)
            ctx.audit.emit(
                action="INGESTION_LINK",
                user_id=user_id,
                target_type="link",
                target_id=url,
                metadata={
                    "chunks": len(chunks),
                    "title": title,
                    "file_id": str(source_artifact_id),
                    "source_artifact_id": str(source_artifact_id),
                    "document_hash": doc_hash,
                    "extractor": doc.extractor,
                },
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

    def _attach_source_metadata(
        self,
        *,
        job: Job,
        doc: ExtractedDocument,
        chunks: list[ExtractedChunk],
        source_artifact_id: UUID,
        source_uri: str,
        source_kind: str,
        fetch_method: str,
        content_hash: str,
        mime_type: str | None,
    ) -> None:
        source_artifact = {
            "source_artifact_id": str(source_artifact_id),
            "source_uri": source_uri,
            "source_kind": source_kind,
            "fetch_method": fetch_method,
            "content_hash": content_hash,
            "mime_type": mime_type,
            "parser_name": doc.extractor,
            "parser_version": doc.schema_version,
            "chunker_name": self.ctx.config.chunker_name,
        }
        chunk_metadata: dict[str, dict[str, object]] = {}
        for index, chunk in enumerate(chunks):
            chunk_hash = hashlib.sha256(
                f"{source_artifact_id}:{index}:{chunk.text}".encode()
            ).hexdigest()
            stable_chunk_id = (
                f"{source_artifact_id.hex[:12]}-{index:04d}-{chunk_hash[:12]}"
            )
            chunk.id = stable_chunk_id
            page_part = ""
            if chunk.page_start or chunk.page_end:
                start = chunk.page_start or chunk.page_end
                end = chunk.page_end or chunk.page_start
                page_part = f"&page={start}" if start == end else f"&pages={start}-{end}"
            citation_ref = f"{source_uri}#chunk={stable_chunk_id}{page_part}"
            chunk_metadata[stable_chunk_id] = {
                **source_artifact,
                "chunk_id": stable_chunk_id,
                "chunk_index": index,
                "chunk_hash": chunk_hash,
                "section": chunk.section,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "token_count": chunk.token_count,
                "chunk_type": chunk.chunk_type,
                "citation_ref": citation_ref,
            }
        job.metadata["source_artifact"] = source_artifact
        job.metadata["chunk_metadata"] = chunk_metadata
