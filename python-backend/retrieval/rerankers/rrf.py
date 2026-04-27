"""Reciprocal Rank Fusion for vector/KG retrieval candidates."""

from __future__ import annotations

from collections.abc import Sequence

from retrieval.core.types import RetrievalHit


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[RetrievalHit]],
    *,
    weights: Sequence[float] | None = None,
    c: int = 60,
    limit: int = 20,
) -> list[RetrievalHit]:
    """Fuse ranked retrieval lists with RRF while preserving provenance."""

    if c <= 0:
        raise ValueError("c must be positive")
    if limit <= 0:
        return []

    active_weights = tuple(weights or [1.0] * len(ranked_lists))
    if len(active_weights) != len(ranked_lists):
        raise ValueError("weights length must match ranked_lists length")

    scores: dict[str, float] = {}
    representatives: dict[str, RetrievalHit] = {}
    contributing_sources: dict[str, set[str]] = {}

    for list_index, hits in enumerate(ranked_lists):
        weight = active_weights[list_index]
        for rank, hit in enumerate(hits, start=1):
            scores[hit.id] = scores.get(hit.id, 0.0) + weight / (c + rank)
            representatives.setdefault(hit.id, hit)
            contributing_sources.setdefault(hit.id, set()).add(hit.source)

    fused: list[RetrievalHit] = []
    for hit_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
        base = representatives[hit_id]
        metadata = {
            **base.metadata,
            "rrf_score": score,
            "contributing_sources": sorted(contributing_sources[hit_id]),
        }
        fused.append(
            RetrievalHit(
                id=base.id,
                content=base.content,
                source="fused" if len(contributing_sources[hit_id]) > 1 else base.source,
                score=score,
                source_uri=base.source_uri,
                metadata=metadata,
            )
        )
        if len(fused) >= limit:
            break
    return fused
