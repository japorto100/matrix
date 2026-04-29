"""Small deterministic router for Feature 019 retrieval modes."""

from __future__ import annotations

import re

from retrieval.core.types import RetrievalMode, RetrievalPlan

_TEMPORAL_TERMS = re.compile(
    r"\b(now|today|latest|recent|since|after|before|during|202[0-9]|yesterday|tomorrow)\b",
    re.IGNORECASE,
)
_GRAPH_TERMS = re.compile(
    r"\b(relationship|connected|path|owns|owned|exports|imports|sanctions|affects|"
    r"supplier|subsidiary|counterparty|between|multi-hop|why)\b",
    re.IGNORECASE,
)


def route_intent(query: str, *, requested_mode: str | None = None) -> RetrievalPlan:
    """Choose text, graph, hybrid or temporal retrieval without LLM latency."""

    normalized = query.strip()
    if requested_mode:
        try:
            mode = RetrievalMode(requested_mode)
        except ValueError:
            mode = RetrievalMode.hybrid
            return RetrievalPlan(normalized, mode, ("invalid_requested_mode",))
        return RetrievalPlan(normalized, mode, ("requested",))

    reasons: list[str] = []
    has_temporal = bool(_TEMPORAL_TERMS.search(normalized))
    has_graph = bool(_GRAPH_TERMS.search(normalized))
    if has_temporal:
        reasons.append("temporal_signal")
    if has_graph:
        reasons.append("graph_signal")

    if has_temporal and has_graph:
        return RetrievalPlan(normalized, RetrievalMode.temporal, tuple(reasons))
    if has_graph:
        return RetrievalPlan(normalized, RetrievalMode.graph, tuple(reasons))
    if len(normalized.split()) >= 12:
        return RetrievalPlan(normalized, RetrievalMode.hybrid, ("long_query",))
    return RetrievalPlan(normalized, RetrievalMode.text, ("default_text",))
