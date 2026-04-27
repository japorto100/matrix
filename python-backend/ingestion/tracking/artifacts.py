"""Durable source artifact registry for ingestion provenance."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import psycopg


class SourceArtifactRegistry:
    """Upsert/read source provenance rows in `ingestion.source_artifacts`."""

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.db_url, autocommit=True)

    def upsert(
        self,
        *,
        source_artifact_id: UUID,
        source_uri: str,
        source_kind: str,
        fetch_method: str,
        content_hash: str,
        mime_type: str | None,
        size_bytes: int | None,
        parser_name: str | None,
        parser_version: str | None,
        chunker_name: str | None,
        chunk_count: int | None,
        embedding_provider: str | None,
        embedding_model: str | None,
        embedding_dim: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Insert or update a source artifact and return the stored row."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO ingestion.source_artifacts (
                    source_artifact_id, source_uri, source_kind, fetch_method,
                    content_hash, mime_type, size_bytes, parser_name,
                    parser_version, chunker_name, chunk_count,
                    embedding_provider, embedding_model, embedding_dim, metadata
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s::jsonb
                )
                ON CONFLICT (source_artifact_id) DO UPDATE SET
                    source_uri = EXCLUDED.source_uri,
                    source_kind = EXCLUDED.source_kind,
                    fetch_method = EXCLUDED.fetch_method,
                    content_hash = EXCLUDED.content_hash,
                    mime_type = EXCLUDED.mime_type,
                    size_bytes = EXCLUDED.size_bytes,
                    parser_name = EXCLUDED.parser_name,
                    parser_version = EXCLUDED.parser_version,
                    chunker_name = EXCLUDED.chunker_name,
                    chunk_count = EXCLUDED.chunk_count,
                    embedding_provider = EXCLUDED.embedding_provider,
                    embedding_model = EXCLUDED.embedding_model,
                    embedding_dim = EXCLUDED.embedding_dim,
                    metadata = ingestion.source_artifacts.metadata || EXCLUDED.metadata,
                    updated_at = now()
                RETURNING *
                """,
                (
                    source_artifact_id,
                    source_uri,
                    source_kind,
                    fetch_method,
                    content_hash,
                    mime_type,
                    size_bytes,
                    parser_name,
                    parser_version,
                    chunker_name,
                    chunk_count,
                    embedding_provider,
                    embedding_model,
                    embedding_dim,
                    json.dumps(metadata or {}),
                ),
            )
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row, strict=True))

    def get(self, source_artifact_id: UUID | str) -> dict[str, Any] | None:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT * FROM ingestion.source_artifacts
                WHERE source_artifact_id = %s
                """,
                (str(source_artifact_id),),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row, strict=True))
