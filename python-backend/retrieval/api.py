"""Retrieval public API for the Feature 019 baseline.

This starts as an adapter-friendly core: callers may pass already retrieved
vector/KG candidates, and the API handles routing, RRF fusion and context
composition. Live search adapters can attach behind the same contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from retrieval.composers.context_bubble import build_context_bubble
from retrieval.core.types import RetrievalHit, RetrievalMode
from retrieval.rerankers.rrf import reciprocal_rank_fusion
from retrieval.searchers.kg_claims import kg_claim_hits
from retrieval.searchers.vector_store import vector_search_hits
from retrieval.understanders.intent_router import route_intent


@dataclass
class RetrievalResult:
    context: str = ""
    hits: list[dict] | None = None
    intent: str = ""
    references: list[dict[str, Any]] | None = None
    degraded: bool = False
    degraded_reasons: list[str] | None = None


def _normalize_hits(items: object, *, default_source: str) -> list[RetrievalHit]:
    if items is None:
        return []
    hits: list[RetrievalHit] = []
    for item in items if isinstance(items, list | tuple) else []:
        if isinstance(item, RetrievalHit):
            hits.append(item)
        elif isinstance(item, dict):
            hits.append(RetrievalHit.from_mapping(item, default_source=default_source))
    return hits


async def retrieve(query: str, **kwargs: object) -> RetrievalResult:
    """Run routing, fusion and context composition for retrieval candidates."""

    requested_mode = kwargs.get("mode")
    plan = route_intent(
        query,
        requested_mode=requested_mode if isinstance(requested_mode, str) else None,
    )
    vector_hits = _normalize_hits(kwargs.get("vector_hits"), default_source="vector")
    kg_hits = _normalize_hits(kwargs.get("kg_hits"), default_source="kg")
    if (
        not vector_hits
        and kwargs.get("use_vector_store") is True
        and plan.mode in (RetrievalMode.text, RetrievalMode.hybrid, RetrievalMode.temporal)
    ):
        try:
            vector_hits = vector_search_hits(
                query,
                store=kwargs.get("vector_store"),
                limit=int(kwargs.get("limit", 20)),
            )
        except Exception:  # noqa: BLE001
            vector_hits = []
            vector_search_failed = True
        else:
            vector_search_failed = False
    else:
        vector_search_failed = False
    if (
        not kg_hits
        and kwargs.get("use_kg_store") is True
        and plan.mode in (RetrievalMode.graph, RetrievalMode.hybrid, RetrievalMode.temporal)
    ):
        try:
            kg_hits = kg_claim_hits(
                query,
                store=kwargs.get("kg_store"),
                limit=int(kwargs.get("limit", 20)),
            )
        except Exception:  # noqa: BLE001
            kg_hits = []
            kg_search_failed = True
        else:
            kg_search_failed = False
    else:
        kg_search_failed = False

    degraded_reasons: list[str] = []
    if vector_search_failed:
        degraded_reasons.append("VECTOR_SEARCH_FAILED")
    if kg_search_failed:
        degraded_reasons.append("KG_SEARCH_FAILED")
    uses_vector = plan.mode in (
        RetrievalMode.text,
        RetrievalMode.hybrid,
        RetrievalMode.temporal,
    )
    uses_kg = plan.mode in (
        RetrievalMode.graph,
        RetrievalMode.hybrid,
        RetrievalMode.temporal,
    )
    if uses_vector and not vector_hits:
        degraded_reasons.append("NO_VECTOR_HITS")
    if uses_kg and not kg_hits:
        degraded_reasons.append("NO_KG_HITS")

    match plan.mode:
        case RetrievalMode.text:
            ranked = vector_hits
        case RetrievalMode.graph:
            ranked = kg_hits
        case RetrievalMode.hybrid | RetrievalMode.temporal:
            ranked = reciprocal_rank_fusion(
                (vector_hits, kg_hits),
                limit=int(kwargs.get("limit", 20)),
            )

    bubble = build_context_bubble(
        ranked,
        token_budget=int(kwargs.get("token_budget", 1600)),
        max_hits=int(kwargs.get("max_hits", 8)),
    )
    return RetrievalResult(
        context=bubble.text,
        hits=[
            {
                "id": hit.id,
                "content": hit.content,
                "source": hit.source,
                "score": hit.score,
                "source_uri": hit.source_uri,
                "metadata": hit.metadata,
            }
            for hit in bubble.hits
        ],
        intent=plan.mode.value,
        references=list(bubble.references),
        degraded=bool(degraded_reasons),
        degraded_reasons=degraded_reasons,
    )
