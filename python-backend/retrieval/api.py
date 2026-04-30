"""Retrieval public API for the Feature 019 baseline.

This starts as an adapter-friendly core: callers may pass already retrieved
vector/KG candidates, and the API handles routing, RRF fusion and context
composition. Live search adapters can attach behind the same contract.
"""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass
from typing import Any

from agent.audit.logger import AuditAction, audit_log
from agent.runtime_events import make_runtime_event
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
    runtime_events: list[dict[str, Any]] | None = None


def _retrieval_event(
    *,
    status: str,
    name: str,
    summary: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return make_runtime_event(
        kind="rag",  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        name=name,
        summary=summary,
        metadata=metadata or {},
    )


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


def _has_context_provenance(hit: RetrievalHit) -> bool:
    metadata = hit.metadata if isinstance(hit.metadata, dict) else {}
    if hit.source_uri:
        return True
    for key in (
        "source_artifact_id",
        "citation_ref",
        "source_ref",
        "raw_evidence_ref",
        "document_id",
        "chunk_id",
        "claim_id",
    ):
        value = metadata.get(key)
        if isinstance(value, list | tuple | set):
            if any(str(item or "").strip() for item in value):
                return True
            continue
        if str(value or "").strip():
            return True
    source_refs = metadata.get("source_refs")
    if isinstance(source_refs, list | tuple):
        return any(isinstance(item, dict) and str(item.get("source_ref") or "").strip() for item in source_refs)
    return False


def _context_provenance_status(hit: RetrievalHit) -> str:
    return "complete" if _has_context_provenance(hit) else "missing"


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


async def _audit_retrieval_runtime_events(
    *,
    query: str,
    kwargs: dict[str, object],
    runtime_events: list[dict[str, Any]],
    intent: str,
    degraded_reasons: list[str],
) -> None:
    """Persist redacted retrieval runtime events for Ops replay when scoped."""

    should_audit = (
        kwargs.get("audit_runtime_events") is True
        or bool(kwargs.get("thread_id"))
        or bool(kwargs.get("session_id"))
    )
    if not should_audit:
        return
    try:
        await audit_log(
            action=AuditAction.RAG_RETRIEVAL,
            user_id=str(kwargs.get("user_id") or "local"),
            session_id=str(kwargs.get("session_id") or ""),
            thread_id=str(kwargs.get("thread_id") or ""),
            success=not bool(degraded_reasons),
            metadata={
                "contract": "agent-runtime-audit/v1",
                "intent": intent,
                "query_digest": hashlib.sha256(query.encode("utf-8")).hexdigest()[:16],
                "query_length": len(query),
                "runtime_events": runtime_events,
                "degraded": bool(degraded_reasons),
                "degraded_reasons": degraded_reasons,
            },
        )
    except Exception:  # noqa: BLE001
        return


async def retrieve(query: str, **kwargs: object) -> RetrievalResult:
    """Run routing, fusion and context composition for retrieval candidates."""

    semantic_filter = _semantic_filter_from_kwargs(kwargs)
    requested_mode = kwargs.get("mode")
    plan = route_intent(
        query,
        requested_mode=requested_mode if isinstance(requested_mode, str) else None,
    )
    runtime_events = [
        _retrieval_event(
            status="started",
            name="rag.retrieve.started",
            summary="Retrieval started",
            metadata={
                "intent": plan.mode.value,
                "requested_mode": requested_mode if isinstance(requested_mode, str) else "",
                "semantic_filter_present": semantic_filter is not None,
                "semantic_lookup_status": (semantic_filter or {}).get("lookup_status", ""),
            },
        )
    ]
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
    provenance_by_hit_id = {hit.id: _context_provenance_status(hit) for hit in bubble.hits}
    if kwargs.get("require_context_provenance") is True and any(
        status == "missing" for status in provenance_by_hit_id.values()
    ):
        degraded_reasons.append("CONTEXT_PROVENANCE_MISSING")
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
    selected_kg_claim_ids = _selected_kg_claim_ids(bubble.hits)
    missing_provenance_ids = [
        hit_id for hit_id, status in provenance_by_hit_id.items() if status == "missing"
    ]
    runtime_events.append(
        _retrieval_event(
            status="completed",
            name="rag.retrieve.completed",
            summary="Retrieval completed",
            metadata={
                "intent": plan.mode.value,
                "vector_hit_count": len(vector_hits),
                "kg_hit_count": len(kg_hits),
                "selected_context_ids": [hit.id for hit in bubble.hits],
                "reference_ids": [str(ref.get("id") or "") for ref in bubble.references],
                "selected_kg_claim_ids": selected_kg_claim_ids,
                "kg_access_recorded_count": kg_access_count,
                "missing_provenance_ids": missing_provenance_ids,
                "degraded": bool(degraded_reasons),
                "degraded_reasons": degraded_reasons,
                "semantic_filter_present": semantic_filter is not None,
            },
        )
    )
    if selected_kg_claim_ids:
        runtime_events.append(
            make_runtime_event(
                kind="kg",
                status="completed",
                name="kg.retrieval.selected_claims",
                summary="KG claims selected into retrieval context",
                metadata={
                    "claim_ids": selected_kg_claim_ids,
                    "kg_access_recorded_count": kg_access_count,
                },
            )
        )
    await _audit_retrieval_runtime_events(
        query=query,
        kwargs=kwargs,
        runtime_events=runtime_events,
        intent=plan.mode.value,
        degraded_reasons=degraded_reasons,
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
                    "provenance_status": provenance_by_hit_id.get(hit.id, "missing"),
                },
            }
            for hit in bubble.hits
        ],
        intent=plan.mode.value,
        references=[
            {
                **reference,
                "metadata": {
                    **dict(reference.get("metadata") or {}),
                    "provenance_status": provenance_by_hit_id.get(str(reference.get("id") or ""), "missing"),
                },
            }
            for reference in bubble.references
        ],
        verification=verification,
        degraded=bool(degraded_reasons),
        degraded_reasons=degraded_reasons,
        runtime_events=runtime_events,
    )
