"""Retrieval public API for the Feature 019 baseline.

This starts as an adapter-friendly core: callers may pass already retrieved
vector/KG candidates, and the API handles routing, RRF fusion and context
composition. Live search adapters can attach behind the same contract.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from retrieval.composers.context_bubble import build_context_bubble
from retrieval.core.types import RetrievalHit, RetrievalMode
from retrieval.rerankers.rrf import reciprocal_rank_fusion
from retrieval.searchers.kg_claims import kg_claim_hits
from retrieval.searchers.vector_store import vector_search_hits
from retrieval.understanders.intent_router import route_intent
from retrieval.verifiers.citation import verify_context_support
from semantic_layer.catalog import DEFAULT_SEMANTIC_CATALOG, lookup_phrase


@dataclass
class RetrievalResult:
    context: str = ""
    hits: list[dict] | None = None
    intent: str = ""
    references: list[dict[str, Any]] | None = None
    verification: dict[str, Any] | None = None
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


def _selected_kg_claim_ids(hits: list[RetrievalHit] | tuple[RetrievalHit, ...]) -> list[str]:
    """Return KG claim ids that survived ranking and context-bubble selection."""

    claim_ids: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        contributing = hit.metadata.get("contributing_sources")
        has_kg_source = hit.source == "kg" or (
            isinstance(contributing, list | tuple) and "kg" in contributing
        )
        if not has_kg_source:
            continue
        claim_id = str(hit.metadata.get("claim_id") or hit.id)
        if claim_id and claim_id not in seen:
            seen.add(claim_id)
            claim_ids.append(claim_id)
    return claim_ids


def _as_tuple(value: object) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple | set):
        return tuple(str(item) for item in value if str(item))
    return (str(value),)


def _semantic_filter_from_kwargs(kwargs: dict[str, object]) -> dict[str, Any] | None:
    raw_filter = kwargs.get("semantic_filter")
    semantic_filter = dict(raw_filter) if isinstance(raw_filter, dict) else {}
    phrase = kwargs.get("semantic_phrase")
    if isinstance(phrase, str) and phrase.strip():
        lookup = lookup_phrase(DEFAULT_SEMANTIC_CATALOG, phrase)
        semantic_filter["phrase"] = phrase
        semantic_filter["lookup_status"] = (
            "ambiguous"
            if lookup["ambiguous"]
            else "matched"
            if lookup["matched"]
            else "not_found"
        )
        if lookup["ambiguous"] or not lookup["matched"]:
            return semantic_filter
        match = lookup["matches"][0]
        item = match["item"]
        if match["type"] == "term":
            semantic_filter.setdefault("semantic_term_ids", (item["term_id"],))
        elif match["type"] == "metric":
            semantic_filter.setdefault("metric_id", item["metric_id"])
    term_ids = _as_tuple(
        semantic_filter.get("semantic_term_ids") or semantic_filter.get("term_ids")
    )
    metric_id = str(semantic_filter.get("metric_id") or "").strip()
    if term_ids:
        semantic_filter["semantic_term_ids"] = term_ids
    if metric_id:
        semantic_filter["metric_id"] = metric_id
    if not semantic_filter:
        return None
    semantic_filter.setdefault("semantic_catalog_version", DEFAULT_SEMANTIC_CATALOG.version)
    return semantic_filter


def _hit_matches_semantic_filter(
    hit: RetrievalHit,
    semantic_filter: dict[str, Any] | None,
) -> bool:
    if not semantic_filter:
        return True
    if semantic_filter.get("lookup_status") in {"ambiguous", "not_found"}:
        return False
    metadata = hit.metadata if isinstance(hit.metadata, dict) else {}
    required_terms = set(_as_tuple(semantic_filter.get("semantic_term_ids")))
    if required_terms:
        hit_terms = set(_as_tuple(metadata.get("semantic_term_ids")))
        if not hit_terms & required_terms:
            return False
    required_metric = str(semantic_filter.get("metric_id") or "").strip()
    if required_metric and str(metadata.get("metric_id") or "").strip() != required_metric:
        return False
    return True


def _apply_semantic_filter(
    hits: list[RetrievalHit],
    semantic_filter: dict[str, Any] | None,
) -> list[RetrievalHit]:
    if not semantic_filter:
        return hits
    return [hit for hit in hits if _hit_matches_semantic_filter(hit, semantic_filter)]


async def _record_kg_access(
    store: object,
    claim_ids: list[str],
) -> tuple[bool, int]:
    """Best-effort KG access telemetry without making retrieval depend on it."""

    if not claim_ids:
        return True, 0
    recorder = getattr(store, "record_claim_access", None)
    if not callable(recorder):
        return True, 0
    result = recorder(claim_ids)
    if inspect.isawaitable(result):
        result = await result
    return True, int(result or 0)


async def retrieve(query: str, **kwargs: object) -> RetrievalResult:
    """Run routing, fusion and context composition for retrieval candidates."""

    semantic_filter = _semantic_filter_from_kwargs(kwargs)
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

    pre_filter_hit_count = len(vector_hits) + len(kg_hits)
    vector_hits = _apply_semantic_filter(vector_hits, semantic_filter)
    kg_hits = _apply_semantic_filter(kg_hits, semantic_filter)

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
    if semantic_filter and pre_filter_hit_count and not (vector_hits or kg_hits):
        degraded_reasons.append("SEMANTIC_FILTER_NO_MATCH")
    if semantic_filter and semantic_filter.get("lookup_status") == "ambiguous":
        degraded_reasons.append("SEMANTIC_FILTER_AMBIGUOUS")
    if semantic_filter and semantic_filter.get("lookup_status") == "not_found":
        degraded_reasons.append("SEMANTIC_FILTER_NOT_FOUND")

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
    kg_access_count = 0
    if kwargs.get("record_kg_access", True) is not False:
        try:
            _, kg_access_count = await _record_kg_access(
                kwargs.get("kg_store"),
                _selected_kg_claim_ids(bubble.hits),
            )
        except Exception:  # noqa: BLE001
            degraded_reasons.append("KG_ACCESS_TELEMETRY_FAILED")
    answer = kwargs.get("answer") or kwargs.get("generated_answer")
    verification: dict[str, Any] | None = None
    if isinstance(answer, str) and answer.strip():
        citation_result = verify_context_support(
            answer,
            bubble.hits,
            require_citations=bool(kwargs.get("require_citations", False)),
        )
        verification = {
            "supported": citation_result.supported,
            "support_ratio": citation_result.support_ratio,
            "citation_ratio": citation_result.citation_ratio,
            "cited_reference_ids": list(citation_result.cited_reference_ids),
            "unsupported_claims": list(citation_result.unsupported_claims),
            "missing_citation_claims": list(citation_result.missing_citation_claims),
        }
        if not citation_result.supported:
            degraded_reasons.append("ANSWER_CITATION_VERIFY_FAILED")
    return RetrievalResult(
        context=bubble.text,
        hits=[
            {
                "id": hit.id,
                "content": hit.content,
                "source": hit.source,
                "score": hit.score,
                "source_uri": hit.source_uri,
                "metadata": {
                    **hit.metadata,
                    **(
                        {"semantic_filter": semantic_filter}
                        if semantic_filter
                        else {}
                    ),
                    **(
                        {"kg_access_recorded": kg_access_count}
                        if hit.source == "kg" and kg_access_count
                        else {}
                    ),
                },
            }
            for hit in bubble.hits
        ],
        intent=plan.mode.value,
        references=list(bubble.references),
        verification=verification,
        degraded=bool(degraded_reasons),
        degraded_reasons=degraded_reasons,
    )
