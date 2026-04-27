"""Adapter from `memory_engine.VectorStore` results to retrieval hits."""

from __future__ import annotations

from typing import Any, Protocol

from retrieval.core.types import RetrievalHit


class VectorSearchStore(Protocol):
    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]: ...


def _score_from_vector_row(row: dict[str, Any]) -> float:
    if row.get("score") is not None:
        return float(row["score"])
    if row.get("similarity") is not None:
        return float(row["similarity"])
    distance = float(row.get("distance", 1.0) or 1.0)
    return max(0.0, 1.0 - distance)


def vector_search_hits(
    query: str,
    *,
    store: VectorSearchStore | None = None,
    limit: int = 5,
) -> list[RetrievalHit]:
    """Search Matrix vector storage and normalize rows for Feature 019."""

    if store is None:
        from memory_engine.vector_store import VectorStore

        store = VectorStore()

    rows = store.search(query, n_results=max(1, min(limit, 20)))
    hits: list[RetrievalHit] = []
    for row in rows:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        source_uri = metadata.get("source_uri") or metadata.get("uri") or row.get("source_uri")
        hits.append(
            RetrievalHit(
                id=str(row.get("id") or row.get("chunk_id") or f"vector:{len(hits)}"),
                content=str(row.get("text") or row.get("content") or ""),
                source="vector",
                score=_score_from_vector_row(row),
                source_uri=str(source_uri) if source_uri else None,
                metadata=metadata,
            )
        )
    return hits
