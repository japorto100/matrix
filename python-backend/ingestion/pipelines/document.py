"""Document Pipeline — file (PDF/MD/HTML/CSV/...) → all 8 phases → Hindsight."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from ingestion.core.exceptions import DedupSkipError, IngestionError
from ingestion.core.types import (
    ExtractedChunk,
    ExtractedDocument,
    Job,
    JobStatus,
    PipelineKind,
)
from ingestion.pipelines.base import Pipeline
from ingestion.tracking.dedup import DocumentHasher
from loguru import logger


class DocumentPipeline(Pipeline):
    """File → detect → load → extract → normalize → chunk → embed → sinks → track."""

    name = "document"

    async def run(  # type: ignore[override]
        self,
        file_id: UUID,
        user_id: str = "local",
        tags: list[str] | None = None,
        sinks_active: list[str] | None = None,
    ) -> Job:
        sinks_active = sinks_active or ["hindsight", "storage"]
        ctx = self.ctx

        # Phase 0: Job
        job = ctx.tracker.start(
            pipeline=PipelineKind.DOCUMENT,
            user_id=user_id,
            file_id=file_id,
            metadata={"tags": tags or [], "sinks": sinks_active},
        )

        try:
            # Phase 1+2: detect + load (we use SeaweedFS loader, mime comes after)
            ctx.tracker.update(job, status=JobStatus.LOADING)
            loader = ctx.loaders.get("seaweedfs")
            loaded = await loader.load(str(file_id))
            logger.info("loaded {} bytes for {}", loaded.size, file_id)

            # Dedup check
            doc_hash = ctx.hasher.hash_bytes(loaded.data)
            existing = ctx.tracker.find_by_hash(doc_hash)
            if existing is not None:
                ctx.audit.emit(
                    action="INGESTION_DEDUP",
                    user_id=user_id,
                    target_type="file",
                    target_id=str(file_id),
                    metadata={
                        "document_hash": doc_hash,
                        "existing_job_id": str(existing["id"]),
                    },
                )
                ctx.tracker.update(
                    job,
                    status=JobStatus.SKIPPED_DEDUP,
                    document_hash=doc_hash,
                )
                ctx.tracker.complete(job)
                raise DedupSkipError(doc_hash, str(existing["id"]))
            ctx.tracker.update(job, document_hash=doc_hash)

            # Detect mime
            ctx.tracker.update(job, status=JobStatus.DETECTING)
            detection = ctx.detectors.detect(data=loaded.data, filename=loaded.filename)
            logger.info("detected mime={} for {}", detection.mime_type, file_id)

            # Phase 3: extract
            ctx.tracker.update(job, status=JobStatus.EXTRACTING)
            extractor = ctx.extractors.get_for_mime(detection.mime_type)
            tmp_path = self._materialize_to_temp(loaded.data, loaded.filename)
            try:
                doc = extractor.extract_timed(tmp_path)
                doc.doc_id = str(file_id)
            finally:
                try:
                    tmp_path.unlink()
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
                source_artifact_id=file_id,
                source_uri=f"matrix-file://{file_id}",
                source_kind="matrix_file",
                fetch_method="go_storage",
                content_hash=doc_hash,
                mime_type=detection.mime_type,
            )
            ctx.tracker.update(
                job, chunks_total=len(chunks), status=JobStatus.EMBEDDING
            )
            logger.info("chunked {} into {} chunks", file_id, len(chunks))

            if not chunks:
                if hasattr(ctx, "source_artifacts"):
                    ctx.source_artifacts.upsert(
                        source_artifact_id=file_id,
                        source_uri=f"matrix-file://{file_id}",
                        source_kind="matrix_file",
                        fetch_method="go_storage",
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
                ctx.audit.emit(
                    action="INGESTION_EMPTY",
                    user_id=user_id,
                    target_type="file",
                    target_id=str(file_id),
                )
                return job

            # Phase 6: embed
            embedder = ctx.embedders.get(ctx.config.embedder_provider)
            embeddings = embedder.embed([c.text for c in chunks])

            # Phase 7: sinks
            embedding_dim = (
                len(embeddings[0]) if embeddings else getattr(embedder, "dim", None)
            )
            if hasattr(ctx, "source_artifacts"):
                ctx.source_artifacts.upsert(
                    source_artifact_id=file_id,
                    source_uri=f"matrix-file://{file_id}",
                    source_kind="matrix_file",
                    fetch_method="go_storage",
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
                    metadata=job.metadata.get("source_artifact", {}),
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

            # Increment chunks_done in one shot
            ctx.tracker.update(job, chunks_done=len(chunks))
            ctx.tracker.complete(job)

            ctx.audit.emit(
                action="INGESTION_DONE",
                user_id=user_id,
                target_type="file",
                target_id=str(file_id),
                metadata={
                    "job_id": str(job.id),
                    "chunks": len(chunks),
                    "extractor": doc.extractor,
                    "document_hash": doc_hash,
                },
            )
            return job

        except DedupSkipError:
            raise
        except Exception as e:  # noqa: BLE001
            ctx.tracker.fail(job, str(e))
            ctx.audit.emit(
                action="INGESTION_FAILED",
                user_id=user_id,
                target_type="file",
                target_id=str(file_id),
                result="error",
                metadata={"job_id": str(job.id), "error": str(e)},
            )
            raise IngestionError(f"document pipeline failed: {e}") from e

    async def run_local_path(
        self,
        path: Path,
        user_id: str = "local",
        tags: list[str] | None = None,
        sinks_active: list[str] | None = None,
    ) -> Job:
        """Ingest a local file without requiring SeaweedFS/Go storage.

        This path is intentionally separate from run(file_id=...) so the
        frontend/storage contract stays unchanged while research-paper ingestion
        and Meta-Harness scenarios can use local files directly.
        """
        sinks_active = sinks_active or ["hindsight"]
        ctx = self.ctx
        resolved = path.expanduser().resolve()
        file_id = uuid5(NAMESPACE_URL, f"file://{resolved}")

        job = ctx.tracker.start(
            pipeline=PipelineKind.DOCUMENT,
            user_id=user_id,
            file_id=file_id,
            metadata={
                "tags": tags or [],
                "sinks": sinks_active,
                "source": "local",
                "source_path": str(resolved),
                "source_artifact_id": str(file_id),
            },
        )

        try:
            ctx.tracker.update(job, status=JobStatus.LOADING)
            loader = ctx.loaders.get("local")
            loaded = await loader.load(str(resolved))
            logger.info("loaded {} bytes from {}", loaded.size, resolved)

            doc_hash = ctx.hasher.hash_bytes(loaded.data)
            ctx.tracker.update(job, status=JobStatus.DETECTING)
            detection = ctx.detectors.detect(
                path=resolved,
                data=loaded.data,
                filename=loaded.filename,
            )
            logger.info("detected mime={} for {}", detection.mime_type, resolved)

            existing = ctx.tracker.find_by_hash(doc_hash)
            if existing is not None:
                ctx.source_artifacts.upsert(
                    source_artifact_id=file_id,
                    source_uri=f"file://{resolved}",
                    source_kind="local_file",
                    fetch_method="local",
                    content_hash=doc_hash,
                    mime_type=detection.mime_type,
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
                        "source_path": str(resolved),
                        "tags": tags or [],
                        "sinks": sinks_active,
                    },
                )
                ctx.audit.emit(
                    action="INGESTION_DEDUP",
                    user_id=user_id,
                    target_type="local_file",
                    target_id=str(resolved),
                    metadata={
                        "document_hash": doc_hash,
                        "existing_job_id": str(existing["id"]),
                    },
                )
                ctx.tracker.update(
                    job,
                    status=JobStatus.SKIPPED_DEDUP,
                    document_hash=doc_hash,
                )
                ctx.tracker.complete(job)
                raise DedupSkipError(doc_hash, str(existing["id"]))
            ctx.tracker.update(job, document_hash=doc_hash)

            ctx.tracker.update(job, status=JobStatus.EXTRACTING)
            extractor = ctx.extractors.get_for_mime(detection.mime_type)
            doc = extractor.extract_timed(resolved)
            doc.doc_id = str(file_id)

            ctx.tracker.update(job, status=JobStatus.NORMALIZING)
            doc = ctx.normalizer.normalize(doc)

            ctx.tracker.update(job, status=JobStatus.CHUNKING)
            chunker = ctx.chunkers.get(ctx.config.chunker_name)
            chunks = chunker.chunk(doc)
            self._attach_source_metadata(
                job=job,
                doc=doc,
                chunks=chunks,
                source_artifact_id=file_id,
                source_uri=f"file://{resolved}",
                source_kind="local_file",
                fetch_method="local",
                content_hash=doc_hash,
                mime_type=detection.mime_type,
            )
            ctx.tracker.update(
                job, chunks_total=len(chunks), status=JobStatus.EMBEDDING
            )
            logger.info("chunked {} into {} chunks", resolved, len(chunks))

            if not chunks:
                ctx.tracker.complete(job)
                ctx.audit.emit(
                    action="INGESTION_EMPTY",
                    user_id=user_id,
                    target_type="local_file",
                    target_id=str(resolved),
                )
                return job

            embedder = ctx.embedders.get(ctx.config.embedder_provider)
            embeddings = embedder.embed([c.text for c in chunks])
            embedding_dim = (
                len(embeddings[0]) if embeddings else getattr(embedder, "dim", None)
            )
            ctx.source_artifacts.upsert(
                source_artifact_id=file_id,
                source_uri=f"file://{resolved}",
                source_kind="local_file",
                fetch_method="local",
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
                    "source_path": str(resolved),
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

            new_hashes_by_id = {c.id: DocumentHasher.hash_chunk(c) for c in chunks}
            ctx.tracker.delete_chunk_hashes_by_doc(str(file_id))
            ctx.tracker.save_chunk_hashes(
                job.id,
                str(file_id),
                [(c.id, new_hashes_by_id[c.id], c.section or None) for c in chunks],
            )

            ctx.tracker.update(job, chunks_done=len(chunks))
            ctx.tracker.complete(job)
            ctx.audit.emit(
                action="INGESTION_LOCAL_FILE",
                user_id=user_id,
                target_type="local_file",
                target_id=str(resolved),
                metadata={
                    "job_id": str(job.id),
                    "file_id": str(file_id),
                    "chunks": len(chunks),
                    "extractor": doc.extractor,
                    "document_hash": doc_hash,
                    "source_path": str(resolved),
                },
            )
            return job

        except DedupSkipError:
            raise
        except Exception as e:  # noqa: BLE001
            ctx.tracker.fail(job, str(e))
            ctx.audit.emit(
                action="INGESTION_LOCAL_FILE_FAILED",
                user_id=user_id,
                target_type="local_file",
                target_id=str(resolved),
                result="error",
                metadata={"job_id": str(job.id), "error": str(e)},
            )
            raise IngestionError(f"local document pipeline failed: {e}") from e

    async def smart_reindex(
        self,
        file_id: UUID,
        user_id: str = "local",
        tags: list[str] | None = None,
        sinks_active: list[str] | None = None,
    ) -> Job:
        """Hash-based incremental reindex (Phase E — Cursor IDE pattern).

        Re-extracts the document, computes per-chunk content hashes, and only
        re-embeds chunks that DIFFER from the previously stored manifest. Chunks
        that were removed get deleted from sinks. Saves 99% of work on small
        edits.
        """
        sinks_active = sinks_active or ["hindsight", "storage"]
        ctx = self.ctx
        from ingestion.tracking.dedup import DocumentHasher

        job = ctx.tracker.start(
            pipeline=PipelineKind.DOCUMENT,
            user_id=user_id,
            file_id=file_id,
            metadata={"tags": tags or [], "sinks": sinks_active, "reindex": True},
        )

        try:
            # Phase 1+2: detect + load
            ctx.tracker.update(job, status=JobStatus.LOADING)
            loader = ctx.loaders.get("seaweedfs")
            loaded = await loader.load(str(file_id))
            doc_hash = ctx.hasher.hash_bytes(loaded.data)
            ctx.tracker.update(job, document_hash=doc_hash)

            # Detect mime
            ctx.tracker.update(job, status=JobStatus.DETECTING)
            detection = ctx.detectors.detect(data=loaded.data, filename=loaded.filename)

            # Phase 3: extract
            ctx.tracker.update(job, status=JobStatus.EXTRACTING)
            extractor = ctx.extractors.get_for_mime(detection.mime_type)
            tmp_path = self._materialize_to_temp(loaded.data, loaded.filename)
            try:
                doc = extractor.extract_timed(tmp_path)
                doc.doc_id = str(file_id)
            finally:
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

            # Phase 4: normalize
            ctx.tracker.update(job, status=JobStatus.NORMALIZING)
            doc = ctx.normalizer.normalize(doc)

            # Phase 5: chunk
            ctx.tracker.update(job, status=JobStatus.CHUNKING)
            chunker = ctx.chunkers.get(ctx.config.chunker_name)
            new_chunks = chunker.chunk(doc)
            self._attach_source_metadata(
                job=job,
                doc=doc,
                chunks=new_chunks,
                source_artifact_id=file_id,
                source_uri=f"matrix-file://{file_id}",
                source_kind="matrix_file",
                fetch_method="go_storage",
                content_hash=doc_hash,
                mime_type=detection.mime_type,
            )

            # ─── Hash diff ────────────────────────────────────────────────
            doc_id = str(file_id)
            new_hashes_by_id = {c.id: DocumentHasher.hash_chunk(c) for c in new_chunks}
            new_hash_set = set(new_hashes_by_id.values())

            old_hashes_by_id = ctx.tracker.get_chunk_hashes_by_doc(doc_id)
            old_hash_set = set(old_hashes_by_id.values())

            unchanged = new_hash_set & old_hash_set
            new_only_chunks = [
                c for c in new_chunks if new_hashes_by_id[c.id] not in unchanged
            ]
            deleted_hashes = old_hash_set - new_hash_set

            ctx.tracker.update(
                job,
                chunks_total=len(new_only_chunks),
                status=JobStatus.EMBEDDING,
            )

            # Phase 6+7: embed + sink only NEW chunks
            if new_only_chunks:
                embedder = ctx.embedders.get(ctx.config.embedder_provider)
                embeddings = embedder.embed([c.text for c in new_only_chunks])
                ctx.tracker.update(job, status=JobStatus.STORING)
                for sink_name in sinks_active:
                    if not ctx.sinks.has(sink_name):
                        continue
                    sink = ctx.sinks.get(sink_name)
                    await sink.write_batch(doc, new_only_chunks, embeddings, job)

            # Delete removed chunks from Hindsight (best-effort)
            if deleted_hashes:
                hindsight_sink = (
                    ctx.sinks.get("hindsight") if ctx.sinks.has("hindsight") else None
                )
                if hindsight_sink and hasattr(hindsight_sink, "delete_by_hashes"):
                    try:
                        await hindsight_sink.delete_by_hashes(deleted_hashes)
                    except Exception as e:  # noqa: BLE001
                        from loguru import logger as _log

                        _log.warning("delete_by_hashes failed: {}", e)

            # Persist new manifest (replace old)
            ctx.tracker.delete_chunk_hashes_by_doc(doc_id)
            ctx.tracker.save_chunk_hashes(
                job.id,
                doc_id,
                [(c.id, new_hashes_by_id[c.id], c.section or None) for c in new_chunks],
            )

            ctx.tracker.update(job, chunks_done=len(new_only_chunks))
            ctx.tracker.complete(job)

            savings_pct = (
                len(unchanged) / max(len(new_chunks), 1) if new_chunks else 0.0
            )
            ctx.audit.emit(
                action="INGESTION_INCREMENTAL_REINDEX",
                user_id=user_id,
                target_type="file",
                target_id=str(file_id),
                metadata={
                    "job_id": str(job.id),
                    "unchanged": len(unchanged),
                    "new": len(new_only_chunks),
                    "deleted": len(deleted_hashes),
                    "total_chunks": len(new_chunks),
                    "savings_pct": round(savings_pct, 4),
                    "extractor": doc.extractor,
                },
            )
            return job

        except Exception as e:  # noqa: BLE001
            ctx.tracker.fail(job, str(e))
            ctx.audit.emit(
                action="INGESTION_REINDEX_FAILED",
                user_id=user_id,
                target_type="file",
                target_id=str(file_id),
                result="error",
                metadata={"job_id": str(job.id), "error": str(e)},
            )
            raise IngestionError(f"smart_reindex failed: {e}") from e

    def _materialize_to_temp(self, data: bytes, filename: str) -> Path:
        """Write bytes to a temp file so file-based extractors can read them.

        UUID-prefixed to avoid collisions on parallel jobs with same filename.
        """
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
        """Attach deterministic source/citation metadata for downstream sinks."""
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
