"""Vector store abstraction.

Providers:
    - chroma   (current local default)
    - pgvector (prepared path, opt-in via VECTOR_STORE_PROVIDER=pgvector)

Default Chroma path: python-backend/data/chroma/ (auto-created)
Embedding model: all-MiniLM-L6-v2 (~23 MB, downloaded once, then cached)
Mock fallback for tests: set VECTOR_STORE_MOCK=true
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Protocol, cast

_DEFAULT_CHROMA_PATH = str(Path(__file__).resolve().parents[2] / "data" / "chroma")
_DEFAULT_LANCE_PATH = str(Path(__file__).resolve().parents[2] / "data" / "lancedb")
_MODEL_NAME = "all-MiniLM-L6-v2"
_DEFAULT_COLLECTION = "memory"
_DEFAULT_PGVECTOR_TABLE = "memory_embeddings"
_VECTOR_DIMENSION = 384


class _VectorBackend(Protocol):
    def add(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None: ...
    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]: ...
    def count(self) -> int: ...
    def status(self) -> dict[str, Any]: ...
    def delete(self, doc_id: str) -> None: ...
    def seed_from_kg(self, stratagems: list[dict[str, Any]]) -> int: ...


def _normalize_provider(value: str | None) -> str:
    provider = (value or "chroma").strip().lower()
    if provider in {"pg", "postgres", "postgresql"}:
        return "pgvector"
    if provider in {"lance", "lancedb"}:
        return "lancedb"
    return provider or "chroma"


def _sanitize_identifier(value: str, fallback: str) -> str:
    cleaned = (value or fallback).strip()
    if not cleaned:
        cleaned = fallback
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cleaned):
        return fallback
    return cleaned


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in embedding) + "]"


class _DeterministicEmbeddingFunction:
    """Reproducible mock embeddings for testing (no model download)."""

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        import hashlib
        result = []
        for text in input:
            digest = hashlib.md5(text.encode()).digest()
            # Expand 16 bytes to 384-dim float vector
            base = [((b / 255.0) * 2.0 - 1.0) for b in digest]
            vec = (base * 24)[:384]
            result.append(vec)
        return result


class _SentenceTransformerEmbeddingFunction:
    def __init__(self, mock: bool = False) -> None:
        self._mock = mock
        self._deterministic = _DeterministicEmbeddingFunction()
        self._embedding_function = None
        if not mock:
            from chromadb.utils.embedding_functions import (  # type: ignore[import-untyped]
                SentenceTransformerEmbeddingFunction,
            )

            self._embedding_function = SentenceTransformerEmbeddingFunction(model_name=_MODEL_NAME)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._mock:
            return self._deterministic(texts)
        if self._embedding_function is None:
            return self._deterministic(texts)
        # chromadb Embeddings is list[Embedding]; cast to our declared return type
        return cast(list[list[float]], self._embedding_function(texts))


class _ChromaVectorStore:
    def __init__(
        self,
        path: str | None = None,
        collection_name: str = _DEFAULT_COLLECTION,
        mock: bool = False,
    ) -> None:
        self._path = path or os.getenv("VECTOR_STORE_PATH", _DEFAULT_CHROMA_PATH)
        self._collection_name = collection_name
        self._mock = mock or os.getenv("VECTOR_STORE_MOCK", "false").lower() in ("1", "true")

        Path(self._path).mkdir(parents=True, exist_ok=True)

        if self._mock:
            # Mock mode must not require chromadb at runtime.
            self._client = None
            self._collection = None
            self._mock_docs: dict[str, tuple[str, dict[str, Any]]] = {}
            return

        import chromadb  # type: ignore[import-untyped]
        from chromadb.utils.embedding_functions import (  # type: ignore[import-untyped]
            SentenceTransformerEmbeddingFunction,
        )

        self._client = chromadb.PersistentClient(path=self._path)
        # Use chromadb's built-in EF so it satisfies the EmbeddingFunction protocol.
        chroma_ef = SentenceTransformerEmbeddingFunction(model_name=_MODEL_NAME)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=cast(Any, chroma_ef),
        )

    def add(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        if self._mock:
            self._mock_docs[doc_id] = (text, metadata or {})
            return
        assert self._collection is not None
        self._collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        if self._mock:
            if not self._mock_docs:
                return []
            q_tokens = set(query.lower().split())
            ranked: list[tuple[float, str, str, dict[str, Any]]] = []
            for doc_id, (text, metadata) in self._mock_docs.items():
                t_tokens = set(text.lower().split())
                if not q_tokens or not t_tokens:
                    distance = 1.0
                else:
                    overlap = len(q_tokens & t_tokens)
                    distance = 1.0 - (overlap / max(len(q_tokens), 1))
                ranked.append((distance, doc_id, text, metadata))
            ranked.sort(key=lambda x: x[0])
            safe_n = min(max(1, n_results), len(ranked), 20)
            return [
                {
                    "id": doc_id,
                    "text": text,
                    "distance": float(distance),
                    "metadata": metadata,
                }
                for distance, doc_id, text, metadata in ranked[:safe_n]
            ]
        assert self._collection is not None
        if self._collection.count() == 0:
            return []
        safe_n = min(n_results, self._collection.count(), 20)
        results: Any = self._collection.query(
            query_texts=[query],
            n_results=safe_n,
            include=["documents", "distances", "metadatas"],
        )
        if results is None:
            return []
        output = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for i, doc_id in enumerate(ids):
            output.append(
                {
                    "id": doc_id,
                    "text": docs[i] if i < len(docs) else "",
                    "distance": float(distances[i]) if i < len(distances) else 1.0,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
            )
        return output

    def count(self) -> int:
        if self._mock:
            return len(self._mock_docs)
        assert self._collection is not None
        return self._collection.count()

    def status(self) -> dict[str, Any]:
        try:
            count = self.count()
            return {"status": "ready", "count": count, "collection": self._collection_name, "provider": "chroma"}
        except Exception as e:
            return {"status": "unavailable", "error": str(e), "provider": "chroma"}

    def delete(self, doc_id: str) -> None:
        if self._mock:
            self._mock_docs.pop(doc_id, None)
            return
        assert self._collection is not None
        self._collection.delete(ids=[doc_id])

    def seed_from_kg(self, stratagems: list[dict[str, Any]]) -> int:
        """Seed the vector store from KG Stratagem nodes."""
        count = 0
        for s in stratagems:
            text = f"{s.get('name', '')} — category: {s.get('category', '')} — market_bias: {s.get('market_bias', '')}"
            self.add(
                doc_id=s.get("id", f"s_{count}"),
                text=text,
                metadata={
                    "type": "Stratagem",
                    "category": s.get("category", ""),
                    "market_bias": s.get("market_bias", ""),
                },
            )
            count += 1
        return count


class _PgVectorStore:
    def __init__(
        self,
        dsn: str | None = None,
        table_name: str | None = None,
        mock: bool = False,
    ) -> None:
        self._dsn = (dsn or os.getenv("VECTOR_STORE_PGVECTOR_DSN", "")).strip()
        self._table_name = _sanitize_identifier(
            table_name or os.getenv("VECTOR_STORE_PGVECTOR_TABLE", _DEFAULT_PGVECTOR_TABLE),
            _DEFAULT_PGVECTOR_TABLE,
        )
        self._embedding = _SentenceTransformerEmbeddingFunction(mock=mock)

    def _connect(self):
        if not self._dsn:
            raise RuntimeError("VECTOR_STORE_PGVECTOR_DSN is not configured")
        import psycopg

        return psycopg.connect(self._dsn, autocommit=True)

    def _ensure_schema(self) -> None:
        from psycopg import sql as pg_sql

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(pg_sql.SQL("CREATE EXTENSION IF NOT EXISTS vector"))
                cur.execute(
                    pg_sql.SQL(
                        """
                        CREATE TABLE IF NOT EXISTS {table} (
                            id TEXT PRIMARY KEY,
                            content TEXT NOT NULL,
                            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                            embedding vector({dim}) NOT NULL,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    ).format(
                        table=pg_sql.Identifier(self._table_name),
                        dim=pg_sql.Literal(_VECTOR_DIMENSION),
                    )
                )

    def _embed_one(self, text: str) -> list[float]:
        return self._embedding.embed([text])[0]

    def add(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        from psycopg import sql as pg_sql
        from psycopg.types.json import Json

        self._ensure_schema()
        embedding = _vector_literal(self._embed_one(text))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    pg_sql.SQL(
                        """
                        INSERT INTO {table} (id, content, metadata, embedding, updated_at)
                        VALUES (%s, %s, %s, %s::vector, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW()
                        """
                    ).format(table=pg_sql.Identifier(self._table_name)),
                    (doc_id, text, Json(metadata or {}), embedding),
                )

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        from psycopg import sql as pg_sql

        self._ensure_schema()
        safe_n = max(1, min(n_results, 20))
        embedding = _vector_literal(self._embed_one(query))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    pg_sql.SQL(
                        """
                        SELECT id, content, metadata, embedding <=> %s::vector AS distance
                        FROM {table}
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """
                    ).format(table=pg_sql.Identifier(self._table_name)),
                    (embedding, embedding, safe_n),
                )
                rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "text": row[1],
                "metadata": row[2] or {},
                "distance": float(row[3]),
            }
            for row in rows
        ]

    def count(self) -> int:
        from psycopg import sql as pg_sql

        self._ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    pg_sql.SQL("SELECT COUNT(*) FROM {table}").format(
                        table=pg_sql.Identifier(self._table_name)
                    )
                )
                row = cur.fetchone()
        return int(row[0]) if row else 0

    def status(self) -> dict[str, Any]:
        try:
            count = self.count()
            return {
                "status": "ready",
                "count": count,
                "provider": "pgvector",
                "table": self._table_name,
            }
        except Exception as e:
            return {
                "status": "unavailable",
                "error": str(e),
                "provider": "pgvector",
                "table": self._table_name,
            }

    def delete(self, doc_id: str) -> None:
        from psycopg import sql as pg_sql

        self._ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    pg_sql.SQL("DELETE FROM {table} WHERE id = %s").format(
                        table=pg_sql.Identifier(self._table_name)
                    ),
                    (doc_id,),
                )

    def seed_from_kg(self, stratagems: list[dict[str, Any]]) -> int:
        count = 0
        for s in stratagems:
            text = f"{s.get('name', '')} — category: {s.get('category', '')} — market_bias: {s.get('market_bias', '')}"
            self.add(
                doc_id=s.get("id", f"s_{count}"),
                text=text,
                metadata={
                    "type": "Stratagem",
                    "category": s.get("category", ""),
                    "market_bias": s.get("market_bias", ""),
                },
            )
            count += 1
        return count


class _LanceDBVectorStore:
    """LanceDB backend — Apache Arrow columnar, hybrid vector+BM25 search, local file-based.

    Path: python-backend/data/lancedb/ (auto-created)
    Table: VECTOR_STORE_LANCE_TABLE env var (default: "memory")
    Hybrid search: set VECTOR_STORE_LANCE_HYBRID=true to combine vector + BM25 (requires fts index)
    """

    def __init__(
        self,
        path: str | None = None,
        table_name: str | None = None,
        mock: bool = False,
    ) -> None:
        self._path = (path or os.getenv("VECTOR_STORE_PATH", _DEFAULT_LANCE_PATH)).strip() or _DEFAULT_LANCE_PATH
        self._table_name = _sanitize_identifier(
            table_name or os.getenv("VECTOR_STORE_LANCE_TABLE", _DEFAULT_COLLECTION),
            _DEFAULT_COLLECTION,
        )
        self._mock = mock or os.getenv("VECTOR_STORE_MOCK", "false").lower() in ("1", "true")
        self._embedding = _SentenceTransformerEmbeddingFunction(mock=self._mock)
        self._hybrid = os.getenv("VECTOR_STORE_LANCE_HYBRID", "false").lower() in ("1", "true")
        Path(self._path).mkdir(parents=True, exist_ok=True)
        if not self._mock:
            import lancedb  # type: ignore[import-untyped]
            self._db = lancedb.connect(self._path)
        else:
            self._db = None
        self._mock_docs: dict[str, tuple[str, dict[str, Any]]] = {}

    def _get_or_create_table(self):
        import pyarrow as pa  # type: ignore[import-untyped]

        assert self._db is not None
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), _VECTOR_DIMENSION)),
            pa.field("metadata_json", pa.string()),
        ])
        if self._table_name in self._db.table_names():
            return self._db.open_table(self._table_name)
        return self._db.create_table(self._table_name, schema=schema)

    def add(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        if self._mock:
            self._mock_docs[doc_id] = (text, metadata or {})
            return
        import json as _json
        vector = self._embedding.embed([text])[0]
        tbl = self._get_or_create_table()
        tbl.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(
            [{"id": doc_id, "text": text, "vector": vector, "metadata_json": _json.dumps(metadata or {})}]
        )

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        if self._mock:
            if not self._mock_docs:
                return []
            q_tokens = set(query.lower().split())
            ranked: list[tuple[float, str, str, dict[str, Any]]] = []
            for doc_id, (text, metadata) in self._mock_docs.items():
                t_tokens = set(text.lower().split())
                overlap = len(q_tokens & t_tokens)
                distance = 1.0 - (overlap / max(len(q_tokens), 1)) if q_tokens else 1.0
                ranked.append((distance, doc_id, text, metadata))
            ranked.sort(key=lambda x: x[0])
            return [
                {"id": d, "text": t, "distance": float(dist), "metadata": m}
                for dist, d, t, m in ranked[:min(n_results, 20)]
            ]
        import json as _json

        assert self._db is not None
        safe_n = max(1, min(n_results, 20))
        vector = self._embedding.embed([query])[0]
        if self._table_name not in self._db.table_names():
            return []
        tbl = self._db.open_table(self._table_name)
        if tbl.count_rows() == 0:
            return []
        results = tbl.search(vector).limit(safe_n).to_list()
        return [
            {
                "id": row["id"],
                "text": row["text"],
                "distance": float(row.get("_distance", 1.0)),
                "metadata": _json.loads(row.get("metadata_json", "{}")),
            }
            for row in results
        ]

    def count(self) -> int:
        if self._mock:
            return len(self._mock_docs)
        assert self._db is not None
        if self._table_name not in self._db.table_names():
            return 0
        return self._db.open_table(self._table_name).count_rows()

    def status(self) -> dict[str, Any]:
        try:
            return {"status": "ready", "count": self.count(), "provider": "lancedb", "table": self._table_name, "hybrid": self._hybrid}
        except Exception as e:
            return {"status": "unavailable", "error": str(e), "provider": "lancedb"}

    def delete(self, doc_id: str) -> None:
        if self._mock:
            self._mock_docs.pop(doc_id, None)
            return
        assert self._db is not None
        if self._table_name not in self._db.table_names():
            return
        self._db.open_table(self._table_name).delete(f"id = '{doc_id}'")

    def seed_from_kg(self, stratagems: list[dict[str, Any]]) -> int:
        count = 0
        for s in stratagems:
            text = f"{s.get('name', '')} — category: {s.get('category', '')} — market_bias: {s.get('market_bias', '')}"
            self.add(
                doc_id=s.get("id", f"s_{count}"),
                text=text,
                metadata={"type": "Stratagem", "category": s.get("category", ""), "market_bias": s.get("market_bias", "")},
            )
            count += 1
        return count


class VectorStore:
    """Provider-switching vector store facade."""

    def __init__(
        self,
        path: str | None = None,
        collection_name: str = _DEFAULT_COLLECTION,
        mock: bool = False,
        provider: str | None = None,
    ) -> None:
        self._provider = _normalize_provider(provider or os.getenv("VECTOR_STORE_PROVIDER", "chroma"))
        if self._provider == "pgvector":
            self._backend: _VectorBackend = _PgVectorStore(mock=mock)
        elif self._provider == "lancedb":
            self._backend = _LanceDBVectorStore(path=path, table_name=collection_name, mock=mock)
        else:
            self._backend = _ChromaVectorStore(path=path, collection_name=collection_name, mock=mock)

    def add(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self._backend.add(doc_id, text, metadata)

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        return self._backend.search(query, n_results=n_results)

    def count(self) -> int:
        return self._backend.count()

    def status(self) -> dict[str, Any]:
        status = self._backend.status()
        status.setdefault("provider", self._provider)
        return status

    def delete(self, doc_id: str) -> None:
        self._backend.delete(doc_id)

    def seed_from_kg(self, stratagems: list[dict[str, Any]]) -> int:
        return self._backend.seed_from_kg(stratagems)
