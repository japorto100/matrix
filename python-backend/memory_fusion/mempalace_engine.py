"""Postgres/pgvector MemPalace-style adapter for memory_fusion.

This keeps the Hindsight-like async API used by Matrix while moving the
MemPalace verbatim/loci path off Chroma/SQLite. Upstream MemPalace concepts
are preserved as metadata: wings, rooms, halls, closets, drawers, and verbatim
drawer content.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from memory_fusion.embeddings import Embedder, create_mempalace_embedder
from memory_fusion.loci import derive_loci_metadata, loci_tags
from memory_fusion.mempalace import sanitize_query


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _hash_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in embedding) + "]"


def _unique_strs(values: list[Any] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return out


def _matches_fact_type(meta: dict[str, Any], fact_type: str | list[str] | None) -> bool:
    if not fact_type:
        return True
    wanted = {fact_type} if isinstance(fact_type, str) else {str(v) for v in fact_type}
    current = str(meta.get("fact_type") or "experience")
    return current in wanted


def _matches_tags(meta: dict[str, Any], tags: list[str] | None) -> bool:
    if not tags:
        return True
    current = set(_unique_strs(list(meta.get("tags") or [])))
    wanted = set(_unique_strs(tags))
    return wanted.issubset(current)


def _item_from_row(row: dict[str, Any], *, distance: float | None = None) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    tags = _unique_strs(list(row.get("tags") or metadata.get("tags") or []))
    metadata.update(
        {
            "bank_id": row.get("bank_id"),
            "wing": row.get("wing"),
            "room": row.get("room"),
            "hall": row.get("hall"),
            "closet_id": row.get("closet_id"),
            "drawer_id": row.get("drawer_id"),
            "loci_path": row.get("loci_path"),
            "source_file": row.get("source_file"),
            "source_ref": row.get("source_ref"),
            "chunk_id": row.get("chunk_id"),
            "document_id": row.get("document_id"),
            "embedding_model": row.get("embedding_model"),
        }
    )
    content = str(row.get("content") or "")
    return {
        "id": row["drawer_id"],
        "episode_id": row["drawer_id"],
        "text": content,
        "content": content,
        "summary": content[:280],
        "fact_type": str(row.get("fact_type") or "experience"),
        "tags": tags,
        "entities": [],
        "metadata": metadata,
        "event_date": row.get("event_date"),
        "timestamp": row.get("filed_at") or row.get("event_date"),
        "weight": round(max(0.0, 1 - distance), 4) if distance is not None else None,
    }


@dataclass
class MemoryRecallItem:
    id: str
    text: str
    fact_type: str
    weight: float
    entities: list[str]
    tags: list[str]
    metadata: dict[str, Any]


@dataclass
class MemoryRecallResponse:
    results: list[MemoryRecallItem]
    entities: dict[str, Any] | None = None
    chunks: dict[str, Any] | None = None


class MempalaceMemoryEngine:
    """MemPalace-compatible verbatim drawer store backed by Postgres/pgvector."""

    def __init__(
        self,
        palace_path: str | None = None,  # kept for older callers; ignored by Postgres path
        *,
        db_url: str | None = None,
        embedder: Embedder | None = None,
    ):
        self.palace_path = palace_path or "postgres"
        self.db_url = db_url or os.environ.get("MEMPALACE_DB_URL") or os.environ.get("HINDSIGHT_DB_URL")
        if not self.db_url:
            raise RuntimeError("MEMPALACE_DB_URL or HINDSIGHT_DB_URL not set")
        self.embedder = embedder or create_mempalace_embedder()

    async def initialize(self) -> None:
        await self._ensure_schema()

    async def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return await psycopg.AsyncConnection.connect(
            self.db_url,
            autocommit=True,
            row_factory=dict_row,
        )

    async def _ensure_schema(self) -> None:
        async with await self._connect() as conn:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS agent")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent.mempalace_drawers (
                    drawer_id TEXT PRIMARY KEY,
                    bank_id TEXT NOT NULL,
                    wing TEXT NOT NULL,
                    room TEXT NOT NULL,
                    hall TEXT NOT NULL DEFAULT 'misc',
                    closet_id TEXT NOT NULL,
                    loci_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    document_id TEXT NULL,
                    source_file TEXT NULL,
                    source_ref TEXT NULL,
                    chunk_id TEXT NULL,
                    fact_type TEXT NOT NULL DEFAULT 'experience',
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    embedding vector NULL,
                    embedding_model TEXT NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    event_date TEXT NULL,
                    filed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_mempalace_drawers_bank_loci_hash
                ON agent.mempalace_drawers (bank_id, wing, room, content_hash)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_mempalace_drawers_loci
                ON agent.mempalace_drawers (bank_id, wing, room, hall)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_mempalace_drawers_model_dim
                ON agent.mempalace_drawers (embedding_model, embedding_dim)
                """
            )

    def _wing_for_bank(self, bank_id: str) -> str:
        return str(bank_id).strip() or "user_default"

    async def _embed_one(self, text: str) -> list[float]:
        vectors = await self.embedder.embed([text])
        if len(vectors) != 1 or not vectors[0]:
            raise RuntimeError("MemPalace embedding provider returned no vector")
        return vectors[0]

    async def recall_async(
        self,
        *args: Any,
        bank_id: str | None = None,
        query: str | None = None,
        fact_type: str | list[str] | None = None,
        budget: Any = None,  # noqa: ARG002
        max_tokens: int | None = None,  # noqa: ARG002
        request_context: Any = None,  # noqa: ARG002
        tags: list[str] | None = None,
        include_entities: bool | None = None,  # noqa: ARG002
        max_entity_tokens: int | None = None,  # noqa: ARG002
        question_date: Any = None,  # noqa: ARG002
        include_chunks: bool | None = None,  # noqa: ARG002
        max_chunk_tokens: int | None = None,  # noqa: ARG002
        wing: str | None = None,
        room: str | None = None,
        hall: str | None = None,
        closet: str | None = None,
        drawer: str | None = None,
        **_: Any,
    ) -> MemoryRecallResponse:
        if args:
            if bank_id is None and len(args) >= 1:
                bank_id = str(args[0])
            if query is None and len(args) >= 2:
                query = str(args[1])
        if not bank_id:
            raise TypeError("bank_id is required")
        if query is None:
            raise TypeError("query is required")
        sanitized = sanitize_query(query)
        clean_query = str(sanitized.get("clean_query") or query)
        embedding = await self._embed_one(clean_query)
        vector = _vector_literal(embedding)
        embedding_dim = len(embedding)
        search_limit = 50

        sql = """
            SELECT
                drawer_id, bank_id, wing, room, hall, closet_id, loci_path,
                content, document_id, source_file, source_ref, chunk_id,
                fact_type, tags, metadata, embedding_model, event_date,
                filed_at::text AS filed_at,
                embedding <=> %(embedding)s::vector AS distance
            FROM agent.mempalace_drawers
            WHERE bank_id = %(bank_id)s
              AND embedding IS NOT NULL
              AND embedding_model = %(embedding_model)s
              AND embedding_dim = %(embedding_dim)s
        """
        params: dict[str, Any] = {
            "bank_id": bank_id,
            "embedding": vector,
            "embedding_model": self.embedder.model,
            "embedding_dim": embedding_dim,
            "limit": search_limit,
        }
        for key, value in {
            "wing": wing,
            "room": room,
            "hall": hall,
            "closet_id": closet,
            "drawer_id": drawer,
        }.items():
            if value:
                params[key] = str(value)
                sql += f" AND {key} = %({key})s"
        sql += """
            ORDER BY embedding <=> %(embedding)s::vector
            LIMIT %(limit)s
        """

        async with await self._connect() as conn:
            rows = [dict(row) for row in await (await conn.execute(sql, params)).fetchall()]

        items: list[MemoryRecallItem] = []
        for row in rows:
            meta = {**dict(row.get("metadata") or {}), "tags": list(row.get("tags") or [])}
            meta.update({k: row.get(k) for k in ("wing", "room", "hall", "closet_id", "drawer_id")})
            if not _matches_fact_type({**meta, "fact_type": row.get("fact_type")}, fact_type):
                continue
            if not _matches_tags(meta, tags):
                continue
            item = _item_from_row(row, distance=float(row.get("distance") or 0.0))
            items.append(
                MemoryRecallItem(
                    id=str(item["id"]),
                    text=str(item["text"]),
                    fact_type=str(item["fact_type"]),
                    weight=float(item["weight"] or 0.0),
                    entities=[],
                    tags=list(item["tags"]),
                    metadata=dict(item["metadata"]),
                )
            )
            if len(items) >= 12:
                break
        return MemoryRecallResponse(results=items, entities={}, chunks={})

    async def retain_batch_async(
        self,
        *,
        bank_id: str,
        contents: list[dict[str, Any]],
        request_context: Any = None,  # noqa: ARG002
        document_tags: list[str] | None = None,
        **kwargs: Any,
    ) -> list[list[str]]:
        from psycopg.types.json import Json

        defer_embedding = bool(kwargs.get("defer_embedding", False))
        results: list[list[str]] = []
        async with await self._connect() as conn:
            for idx, item in enumerate(contents):
                content = str(item.get("content") or "").strip()
                if not content:
                    results.append([])
                    continue

                metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                fact_type = str(item.get("fact_type") or metadata.get("fact_type") or "experience")
                document_id = str(
                    item.get("document_id")
                    or metadata.get("document_id")
                    or f"{bank_id}:{idx}:{_hash_id(content)}"
                )
                merged_metadata = {
                    **dict(metadata),
                    "bank_id": bank_id,
                    "wing": metadata.get("wing") or bank_id,
                    "document_id": document_id,
                    "fact_type": fact_type,
                }
                loci = derive_loci_metadata(
                    {**item, "fact_type": fact_type},
                    merged_metadata,
                    bank_id=bank_id,
                )
                item_tags = loci_tags(
                    {**item, "tags": _unique_strs(list(item.get("tags") or []) + list(document_tags or []))},
                    loci,
                )
                drawer_id = str(loci["drawer_id"] or f"drawer_{loci['wing']}_{loci['room']}_{_hash_id(document_id)}")
                content_sha = _content_hash(content)

                existing = await (
                    await conn.execute(
                        """
                        SELECT drawer_id, embedding IS NULL AS embedding_pending
                        FROM agent.mempalace_drawers
                        WHERE bank_id = %s AND wing = %s AND room = %s AND content_hash = %s
                        LIMIT 1
                        """,
                        (bank_id, loci["wing"], loci["room"], content_sha),
                    )
                ).fetchone()
                if existing and (defer_embedding or not bool(existing["embedding_pending"])):
                    results.append([str(existing["drawer_id"])])
                    continue

                drawer_id = str(existing["drawer_id"]) if existing else drawer_id
                if defer_embedding:
                    embedding: list[float] = []
                    vector = None
                    embedding_dim = 0
                    embedding_status = "pending"
                else:
                    embedding = await self._embed_one(content)
                    vector = _vector_literal(embedding)
                    embedding_dim = len(embedding)
                    embedding_status = "ready"
                row_metadata = {
                    **merged_metadata,
                    **loci,
                    "tags": item_tags,
                    "added_by": "memory-fusion",
                    "ingest_mode": "memory_fusion",
                    "embedding_status": embedding_status,
                    "embedding_deferred": defer_embedding,
                    "filed_at": _now_iso(),
                }
                source_file = str(metadata.get("source_file") or f"memory://{bank_id}/{document_id}")
                await conn.execute(
                    """
                    INSERT INTO agent.mempalace_drawers (
                        drawer_id, bank_id, wing, room, hall, closet_id, loci_path,
                        content, content_hash, document_id, source_file, source_ref,
                        chunk_id, fact_type, tags, metadata, embedding, embedding_model,
                        embedding_dim, event_date, updated_at
                    )
                    VALUES (
                        %(drawer_id)s, %(bank_id)s, %(wing)s, %(room)s, %(hall)s,
                        %(closet_id)s, %(loci_path)s, %(content)s, %(content_hash)s,
                        %(document_id)s, %(source_file)s, %(source_ref)s, %(chunk_id)s,
                        %(fact_type)s, %(tags)s, %(metadata)s, %(embedding)s::vector,
                        %(embedding_model)s, %(embedding_dim)s, %(event_date)s, now()
                    )
                    ON CONFLICT (drawer_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        tags = EXCLUDED.tags,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding,
                        embedding_model = EXCLUDED.embedding_model,
                        embedding_dim = EXCLUDED.embedding_dim,
                        updated_at = now()
                    """,
                    {
                        "drawer_id": drawer_id,
                        "bank_id": bank_id,
                        "wing": loci["wing"],
                        "room": loci["room"],
                        "hall": loci["hall"],
                        "closet_id": loci["closet_id"],
                        "loci_path": loci["loci_path"],
                        "content": content,
                        "content_hash": content_sha,
                        "document_id": document_id,
                        "source_file": source_file,
                        "source_ref": loci["source_ref"],
                        "chunk_id": str(metadata.get("chunk_id") or metadata.get("source_ref") or "0"),
                        "fact_type": fact_type,
                        "tags": Json(item_tags),
                        "metadata": Json(row_metadata),
                        "embedding": vector,
                        "embedding_model": self.embedder.model,
                        "embedding_dim": embedding_dim,
                        "event_date": str(item.get("event_date") or ""),
                    },
                )
                results.append([drawer_id])

        return results

    async def list_memory_units(
        self,
        *,
        bank_id: str,
        fact_type: str | None = None,
        search_query: str | None = None,
        limit: int = 50,
        offset: int = 0,
        request_context: Any = None,  # noqa: ARG002
        wing: str | None = None,
        room: str | None = None,
        hall: str | None = None,
        thread_id: str | None = None,
        session_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        if search_query:
            recall = await self.recall_async(
                bank_id=bank_id,
                query=search_query,
                fact_type=fact_type,
                wing=wing,
                room=room,
                hall=hall,
            )
            filtered = [
                _item_from_row(
                    {
                        **item.metadata,
                        "drawer_id": item.id,
                        "bank_id": bank_id,
                        "content": item.text,
                        "fact_type": item.fact_type,
                        "tags": item.tags,
                    },
                    distance=max(0.0, 1 - item.weight),
                )
                for item in recall.results
            ]
            return {"items": filtered[offset : offset + limit], "total": len(filtered)}

        sql = """
            SELECT
                drawer_id, bank_id, wing, room, hall, closet_id, loci_path,
                content, document_id, source_file, source_ref, chunk_id,
                fact_type, tags, metadata, embedding_model, event_date,
                filed_at::text AS filed_at
            FROM agent.mempalace_drawers
            WHERE bank_id = %(bank_id)s
        """
        params: dict[str, Any] = {"bank_id": bank_id, "limit": limit, "offset": offset}
        for key, value in {"wing": wing, "room": room, "hall": hall}.items():
            if value:
                params[key] = str(value)
                sql += f" AND {key} = %({key})s"
        if fact_type:
            params["fact_type"] = fact_type
            sql += " AND fact_type = %(fact_type)s"
        if thread_id:
            params["thread_id"] = str(thread_id)
            sql += " AND metadata->>'thread_id' = %(thread_id)s"
        if session_id:
            params["session_id"] = str(session_id)
            sql += " AND metadata->>'session_id' = %(session_id)s"
        sql += " ORDER BY filed_at DESC, drawer_id ASC LIMIT %(limit)s OFFSET %(offset)s"

        count_sql = "SELECT count(*) AS total FROM (" + sql.rsplit(" ORDER BY ", 1)[0] + ") q"
        async with await self._connect() as conn:
            total_row = await (await conn.execute(count_sql, params)).fetchone()
            rows = [dict(row) for row in await (await conn.execute(sql, params)).fetchall()]
        return {
            "items": [_item_from_row(row) for row in rows],
            "total": int(total_row["total"] if total_row else len(rows)),
        }

    async def get_memory_unit(self, *, unit_id: str, request_context: Any = None, **_: Any) -> dict[str, Any] | None:
        async with await self._connect() as conn:
            row = await (
                await conn.execute(
                    """
                    SELECT drawer_id, bank_id, wing, room, hall, closet_id, loci_path,
                           content, document_id, source_file, source_ref, chunk_id,
                           fact_type, tags, metadata, embedding_model, event_date,
                           filed_at::text AS filed_at
                    FROM agent.mempalace_drawers
                    WHERE drawer_id = %s
                    """,
                    (unit_id,),
                )
            ).fetchone()
        return _item_from_row(dict(row)) if row else None

    async def delete_memory_unit(self, *, unit_id: str, request_context: Any = None, **_: Any) -> dict[str, Any]:
        async with await self._connect() as conn:
            result = await conn.execute(
                "DELETE FROM agent.mempalace_drawers WHERE drawer_id = %s",
                (unit_id,),
            )
        return {"deleted": result.rowcount > 0, "id": unit_id}

    async def delete_memory_units_by_scope(
        self,
        *,
        bank_id: str,
        room: str | None = None,
        thread_id: str | None = None,
        session_id: str | None = None,
        request_context: Any = None,  # noqa: ARG002
        **_: Any,
    ) -> dict[str, Any]:
        """Delete MemPalace drawers for an explicit room/thread/session scope."""

        if not any((room, thread_id, session_id)):
            raise ValueError("refusing unscoped MemPalace delete")
        sql = "DELETE FROM agent.mempalace_drawers WHERE bank_id = %(bank_id)s"
        params: dict[str, Any] = {"bank_id": bank_id}
        if room:
            params["room"] = str(room)
            sql += " AND room = %(room)s"
        if thread_id:
            params["thread_id"] = str(thread_id)
            sql += " AND metadata->>'thread_id' = %(thread_id)s"
        if session_id:
            params["session_id"] = str(session_id)
            sql += " AND metadata->>'session_id' = %(session_id)s"
        async with await self._connect() as conn:
            result = await conn.execute(sql, params)
        return {"deleted": int(result.rowcount or 0), "bank_id": bank_id}

    async def list_banks(self, *, request_context: Any = None, **_: Any) -> list[dict[str, Any]]:
        async with await self._connect() as conn:
            rows = await (
                await conn.execute(
                    """
                    SELECT bank_id, count(*) AS count
                    FROM agent.mempalace_drawers
                    GROUP BY bank_id
                    ORDER BY bank_id
                    """
                )
            ).fetchall()
        return [
            {"bank_id": str(row["bank_id"]), "name": str(row["bank_id"]), "count": int(row["count"])}
            for row in rows
        ]

    async def list_mental_models_consolidated(
        self,
        *,
        bank_id: str,  # noqa: ARG002
        limit: int = 20,  # noqa: ARG002
        request_context: Any = None,  # noqa: ARG002
        **_: Any,
    ) -> list[dict[str, Any]]:
        return []

    async def status(self) -> dict[str, Any]:
        async with await self._connect() as conn:
            row = await (
                await conn.execute("SELECT count(*) AS count FROM agent.mempalace_drawers")
            ).fetchone()
        return {
            "provider": "mempalace-postgres",
            "storage": "postgres-pgvector",
            "embedding_provider": "openrouter" if self.embedder.model != "deterministic-test-8d" else "deterministic",
            "embedding_model": self.embedder.model,
            "count": int(row["count"] if row else 0),
        }
