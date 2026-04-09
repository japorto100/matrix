"""Job lifecycle CRUD against `ingestion.jobs` table (Postgres)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

import psycopg
from loguru import logger

from ingestion.core.types import Job, JobStatus, PipelineKind


class JobTracker:
    """Persists Job state to Postgres `ingestion.jobs` table."""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.db_url, autocommit=True)

    def start(
        self,
        pipeline: PipelineKind,
        user_id: str = "local",
        file_id: UUID | None = None,
        document_hash: str | None = None,
        metadata: dict | None = None,
    ) -> Job:
        """Insert a new job row in `pending`/`detecting` state."""
        job = Job(
            file_id=file_id,
            pipeline=pipeline,
            user_id=user_id,
            status=JobStatus.PENDING,
            document_hash=document_hash,
            metadata=metadata or {},
            started_at=datetime.now(timezone.utc),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ingestion.jobs
                  (id, file_id, pipeline, user_id, status, progress,
                   chunks_total, chunks_done, error_message,
                   started_at, completed_at, document_hash, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(job.id),
                    str(job.file_id) if job.file_id else None,
                    job.pipeline.value,
                    job.user_id,
                    job.status.value,
                    job.progress,
                    job.chunks_total,
                    job.chunks_done,
                    job.error_message,
                    job.started_at,
                    job.completed_at,
                    job.document_hash,
                    json.dumps(job.metadata),
                ),
            )
        logger.info("job {} started ({})", job.id, pipeline.value)
        return job

    def update(self, job: Job, **fields: object) -> None:
        """Update arbitrary fields on the job (in-memory + DB)."""
        for k, v in fields.items():
            setattr(job, k, v)
        cols: list[str] = []
        values: list[object] = []
        for k, v in fields.items():
            if k == "status" and isinstance(v, JobStatus):
                v = v.value
            elif k == "metadata":
                v = json.dumps(v)
            cols.append(f"{k} = %s" + ("::jsonb" if k == "metadata" else ""))
            values.append(v)
        if not cols:
            return
        values.append(str(job.id))
        with self._connect() as conn:
            conn.execute(
                f"UPDATE ingestion.jobs SET {', '.join(cols)} WHERE id = %s",
                values,
            )

    def tick(self, job: Job) -> None:
        """Increment chunks_done by 1 + recompute progress."""
        job.chunks_done += 1
        if job.chunks_total:
            job.progress = job.chunks_done / job.chunks_total
        with self._connect() as conn:
            conn.execute(
                """UPDATE ingestion.jobs
                   SET chunks_done = %s, progress = %s
                   WHERE id = %s""",
                (job.chunks_done, job.progress, str(job.id)),
            )

    def complete(self, job: Job) -> None:
        job.status = JobStatus.DONE
        job.completed_at = datetime.now(timezone.utc)
        job.progress = 1.0
        with self._connect() as conn:
            conn.execute(
                """UPDATE ingestion.jobs
                   SET status = %s, completed_at = %s, progress = %s
                   WHERE id = %s""",
                (job.status.value, job.completed_at, job.progress, str(job.id)),
            )
        logger.info("job {} done", job.id)

    def fail(self, job: Job, error: str) -> None:
        job.status = JobStatus.FAILED
        job.error_message = error
        job.completed_at = datetime.now(timezone.utc)
        with self._connect() as conn:
            conn.execute(
                """UPDATE ingestion.jobs
                   SET status = %s, error_message = %s, completed_at = %s
                   WHERE id = %s""",
                (job.status.value, error, job.completed_at, str(job.id)),
            )
        logger.error("job {} failed: {}", job.id, error)

    def get(self, job_id: UUID | str) -> dict | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM ingestion.jobs WHERE id = %s",
                (str(job_id),),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row, strict=True))

    def list_by_status(self, status: JobStatus, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT * FROM ingestion.jobs
                   WHERE status = %s
                   ORDER BY started_at DESC
                   LIMIT %s""",
                (status.value, limit),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]

    def status_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT status, COUNT(*) FROM ingestion.jobs GROUP BY status"
            )
            return {row[0]: int(row[1]) for row in cur.fetchall()}

    def find_by_hash(self, document_hash: str) -> dict | None:
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT * FROM ingestion.jobs
                   WHERE document_hash = %s AND status = 'done'
                   ORDER BY completed_at DESC
                   LIMIT 1""",
                (document_hash,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row, strict=True))

    # ─── Chunk-level hash manifest (Phase E — incremental reindex) ─────────

    def save_chunk_hashes(
        self,
        job_id: UUID,
        doc_id: str,
        chunks_with_hashes: list[tuple[str, str, str | None]],
    ) -> None:
        """Batch INSERT chunk_id → content_hash for a job.

        Args:
            job_id: parent ingestion job
            doc_id: stable document identifier (usually file_id as str)
            chunks_with_hashes: list of (chunk_id, content_hash, section)
        """
        if not chunks_with_hashes:
            return
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO ingestion.chunk_hashes
                    (job_id, chunk_id, content_hash, doc_id, section)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (job_id, chunk_id) DO UPDATE SET
                    content_hash = EXCLUDED.content_hash,
                    section = EXCLUDED.section
                """,
                [
                    (str(job_id), chunk_id, content_hash, doc_id, section)
                    for chunk_id, content_hash, section in chunks_with_hashes
                ],
            )

    def get_chunk_hashes_by_doc(self, doc_id: str) -> dict[str, str]:
        """Return {chunk_id: content_hash} from the most recent successful job."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT ch.chunk_id, ch.content_hash
                FROM ingestion.chunk_hashes ch
                JOIN ingestion.jobs j ON j.id = ch.job_id
                WHERE ch.doc_id = %s AND j.status = 'done'
                ORDER BY j.completed_at DESC NULLS LAST
                """,
                (doc_id,),
            )
            return dict(cur.fetchall())

    def delete_chunk_hashes_by_doc(self, doc_id: str) -> int:
        """Cascade-delete all chunk hashes for a doc (called before re-save)."""
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM ingestion.chunk_hashes WHERE doc_id = %s",
                (doc_id,),
            )
            return cur.rowcount or 0

    def recover_stuck_jobs(self) -> int:
        """Mark all non-terminal jobs as failed (called on worker startup).

        If the worker crashes mid-job, the job row stays in a transient state
        like 'extracting' / 'chunking' forever. On the next startup we want to
        sweep these up so the frontend doesn't show them as still-running.

        Returns the number of jobs reset.
        """
        non_terminal = (
            "pending",
            "detecting",
            "loading",
            "extracting",
            "normalizing",
            "chunking",
            "embedding",
            "storing",
        )
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE ingestion.jobs
                   SET status = 'failed',
                       error_message = COALESCE(error_message, 'worker restarted mid-job'),
                       completed_at = NOW()
                   WHERE status = ANY(%s)""",
                (list(non_terminal),),
            )
            return cur.rowcount or 0
