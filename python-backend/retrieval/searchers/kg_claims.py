"""Adapter from global KG claim search rows to retrieval hits."""

from __future__ import annotations

from typing import Any, Protocol

from retrieval.core.types import RetrievalHit


class KGClaimSearchStore(Protocol):
    def search_claims(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...


def kg_claim_rows_to_hits(rows: list[dict[str, Any]]) -> list[RetrievalHit]:
    """Normalize global KG claim rows for Feature 019 fusion."""

    hits: list[RetrievalHit] = []
    for row in rows:
        metadata = {
            "lane": row.get("lane"),
            "status": row.get("status"),
            "predicate": row.get("predicate"),
            "valid_period": row.get("valid_period"),
            "provenance": row.get("provenance"),
            "path": row.get("path"),
            "source_refs": row.get("source_refs"),
            "context_metadata": row.get("context_metadata"),
            "subject": row.get("subject"),
            "object": row.get("object"),
            **(row.get("metadata") if isinstance(row.get("metadata"), dict) else {}),
        }
        score = row.get("final_score", row.get("score", row.get("confidence", 0.0)))
        source_uri = row.get("source_uri")
        hits.append(
            RetrievalHit(
                id=str(row.get("claim_id") or row.get("id") or f"kg:{len(hits)}"),
                content=str(row.get("claim_text") or row.get("content") or ""),
                source="kg",
                score=float(score or 0.0),
                source_uri=str(source_uri) if source_uri else None,
                metadata={k: v for k, v in metadata.items() if v is not None},
            )
        )
    return hits


def kg_claim_hits(
    query: str,
    *,
    store: KGClaimSearchStore | None = None,
    limit: int = 5,
) -> list[RetrievalHit]:
    """Search global KG claims when a store adapter is supplied."""

    if store is None:
        return []
    return kg_claim_rows_to_hits(store.search_claims(query, limit=max(1, min(limit, 20))))
