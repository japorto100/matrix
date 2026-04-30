"""Small semantic layer for metrics, KG claims and RAG concepts."""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from math import log
from typing import Any, Literal

SemanticStatus = Literal["draft", "active", "deprecated"]
MetricScope = Literal["public", "tenant", "user", "admin"]
ProposalStatus = Literal["proposed", "accepted", "rejected"]


@dataclass(frozen=True)
class SemanticTerm:
    term_id: str
    name: str
    aliases: tuple[str, ...] = ()
    owner: str = "matrix"
    status: SemanticStatus = "active"
    description: str = ""
    source_refs: tuple[str, ...] = ()
    allowed_use: tuple[str, ...] = ("agent_answer", "control_ui", "meta_harness")
    kg_claim_types: tuple[str, ...] = ()
    rag_source_classes: tuple[str, ...] = ()
    version: str = "1.0.0"
    deprecated_by: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticMetric:
    metric_id: str
    name: str
    measure: str
    dimensions: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    grain: str = "event"
    time_field: str = ""
    freshness_sla: str = ""
    allowed_aggregations: tuple[str, ...] = ("sum", "avg", "count")
    aliases: tuple[str, ...] = ()
    owner: str = "matrix"
    status: SemanticStatus = "active"
    permission_scope: MetricScope = "public"
    source_table: str = ""
    source_refs: tuple[str, ...] = ()
    version: str = "1.0.0"
    deprecated_by: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticCatalog:
    terms: tuple[SemanticTerm, ...] = ()
    metrics: tuple[SemanticMetric, ...] = ()
    version: str = "1.0.0"

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "terms": [term.as_dict() for term in self.terms],
            "metrics": [metric.as_dict() for metric in self.metrics],
        }


@dataclass(frozen=True)
class PermissionContext:
    user_id: str = ""
    tenant_id: str = ""
    roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class CorrectionProposal:
    proposal_id: str
    target_type: Literal["term", "metric"]
    target_id: str
    proposed_by: str
    rationale: str
    patch: dict[str, Any]
    status: ProposalStatus = "proposed"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    reviewed_by: str = ""
    reviewed_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_default_catalog() -> SemanticCatalog:
    """Return a minimal Matrix-owned semantic catalog."""

    return SemanticCatalog(
        terms=(
            SemanticTerm(
                term_id="kg_claim",
                name="KG claim",
                aliases=("claim", "knowledge claim", "global claim"),
                description="Versioned global knowledge assertion with provenance.",
                source_refs=(
                    "feature-017",
                    "python-backend/memory_engine/global_kg.py",
                ),
                kg_claim_types=("entity_attribute", "entity_relation"),
                rag_source_classes=("kg_claim",),
            ),
            SemanticTerm(
                term_id="rag_citation",
                name="RAG citation",
                aliases=("citation", "source citation", "evidence citation"),
                description="Document or claim evidence surfaced with an answer.",
                source_refs=("feature-019", "retrieval/verifiers/citation.py"),
                rag_source_classes=("document_chunk", "kg_claim"),
            ),
        ),
        metrics=(
            SemanticMetric(
                metric_id="agent_tool_success_rate",
                name="Agent tool success rate",
                aliases=("tool success", "tool success rate"),
                measure="successful_tool_results / total_tool_results",
                dimensions=("tool_name", "runner_variant", "tenant_id"),
                filters=("time_range", "tenant_id"),
                grain="tool_result",
                time_field="created_at",
                freshness_sla="15m",
                allowed_aggregations=("avg",),
                permission_scope="tenant",
                source_table="agent.audit_events",
                source_refs=("feature-014", "feature-016"),
            ),
            SemanticMetric(
                metric_id="retrieval_pass_rate",
                name="Retrieval pass rate",
                aliases=("rag pass rate", "retrieval quality"),
                measure="passed_canaries / total_canaries",
                dimensions=("candidate_id", "question_class", "split"),
                filters=("run_id", "split", "question_class"),
                grain="canary_result",
                time_field="generated_at",
                freshness_sla="run-scoped",
                allowed_aggregations=("avg",),
                permission_scope="public",
                source_table="data/meta_harness/runs",
                source_refs=("feature-022", "feature-023"),
            ),
        ),
    )


DEFAULT_SEMANTIC_CATALOG = build_default_catalog()


def validate_catalog(catalog: SemanticCatalog) -> dict[str, Any]:
    """Validate ids and alias collisions across terms and metrics."""

    failures: list[str] = []
    seen_ids: set[str] = set()
    alias_index: dict[str, list[str]] = {}
    for kind, items in (("term", catalog.terms), ("metric", catalog.metrics)):
        for item in items:
            item_id = item.term_id if kind == "term" else item.metric_id
            if item_id in seen_ids:
                failures.append(f"duplicate-id:{item_id}")
            seen_ids.add(item_id)
            names = (item.name, *item.aliases)
            for phrase in names:
                key = _normalize_phrase(phrase)
                if not key:
                    failures.append(f"empty-alias:{kind}:{item_id}")
                    continue
                alias_index.setdefault(key, []).append(f"{kind}:{item_id}")
    collisions = {key: refs for key, refs in alias_index.items() if len(set(refs)) > 1}
    for key, refs in collisions.items():
        failures.append(f"ambiguous-alias:{key}:{','.join(sorted(set(refs)))}")
    return {
        "passed": not failures,
        "failures": failures,
        "alias_collisions": collisions,
    }


def lookup_phrase(catalog: SemanticCatalog, phrase: str) -> dict[str, Any]:
    """Lookup terms/metrics by name or alias and surface ambiguity."""

    key = _normalize_phrase(phrase)
    matches: list[dict[str, Any]] = []
    for term in catalog.terms:
        if key in {_normalize_phrase(term.name), *map(_normalize_phrase, term.aliases)}:
            matches.append({"type": "term", "item": term.as_dict()})
    for metric in catalog.metrics:
        if key in {
            _normalize_phrase(metric.name),
            *map(_normalize_phrase, metric.aliases),
        }:
            matches.append({"type": "metric", "item": metric.as_dict()})
    return {
        "phrase": phrase,
        "matched": len(matches) == 1,
        "ambiguous": len(matches) > 1,
        "matches": matches,
        "candidate_matches": [] if matches else _lexical_candidates(catalog, phrase),
    }


def plan_metric_query(
    catalog: SemanticCatalog,
    metric_id: str,
    context: PermissionContext,
) -> dict[str, Any]:
    """Return a permission-aware query plan, never free-form SQL."""

    metric = next(
        (item for item in catalog.metrics if item.metric_id == metric_id), None
    )
    if metric is None:
        return {"allowed": False, "reason": "unknown-metric", "metric_id": metric_id}
    permission = _metric_permission(metric, context)
    if not permission["allowed"]:
        return {
            "allowed": False,
            "reason": permission["reason"],
            "metric": metric.as_dict(),
            "sql": None,
            "raw_sql_allowed": False,
        }
    return {
        "allowed": True,
        "metric": metric.as_dict(),
        "semantic_contract": {
            "measure": metric.measure,
            "dimensions": list(metric.dimensions),
            "filters": list(metric.filters),
            "grain": metric.grain,
            "time_field": metric.time_field,
            "source_table": metric.source_table,
            "source_refs": list(metric.source_refs),
        },
        "sql": None,
        "raw_sql_allowed": False,
        "freshness_sla": metric.freshness_sla,
    }


def propose_correction(
    *,
    target_type: Literal["term", "metric"],
    target_id: str,
    proposed_by: str,
    rationale: str,
    patch: dict[str, Any],
) -> CorrectionProposal:
    """Create an auditable semantic correction proposal."""

    return CorrectionProposal(
        proposal_id=f"semantic-proposal-{uuid.uuid4().hex[:12]}",
        target_type=target_type,
        target_id=target_id,
        proposed_by=proposed_by,
        rationale=rationale,
        patch=dict(patch),
    )


def review_correction(
    proposal: CorrectionProposal,
    *,
    decision: Literal["accepted", "rejected"],
    reviewed_by: str,
) -> CorrectionProposal:
    """Record review state without mutating the original proposal."""

    return replace(
        proposal,
        status=decision,
        reviewed_by=reviewed_by,
        reviewed_at=datetime.now(UTC).isoformat(),
    )


def _metric_permission(
    metric: SemanticMetric,
    context: PermissionContext,
) -> dict[str, Any]:
    if metric.permission_scope == "public":
        return {"allowed": True, "reason": "public"}
    if metric.permission_scope == "tenant":
        if context.tenant_id:
            return {"allowed": True, "reason": "tenant-context"}
        return {"allowed": False, "reason": "missing-tenant-context"}
    if metric.permission_scope == "user":
        if context.user_id:
            return {"allowed": True, "reason": "user-context"}
        return {"allowed": False, "reason": "missing-user-context"}
    if metric.permission_scope == "admin":
        if "admin" in context.roles:
            return {"allowed": True, "reason": "admin-role"}
        return {"allowed": False, "reason": "admin-role-required"}
    return {"allowed": False, "reason": "unknown-scope"}


def _normalize_phrase(phrase: str) -> str:
    return " ".join(str(phrase or "").strip().lower().replace("_", " ").split())


def _phrase_tokens(phrase: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in re.findall(r"[a-z0-9]+", _normalize_phrase(phrase))
        if len(token) > 1
    )


def _semantic_item_documents(catalog: SemanticCatalog) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for term in catalog.terms:
        text = " ".join(
            (
                term.name,
                *term.aliases,
                term.description,
                *term.kg_claim_types,
                *term.rag_source_classes,
            )
        )
        documents.append(
            {
                "type": "term",
                "item": term.as_dict(),
                "label": term.name,
                "tokens": _phrase_tokens(text),
            }
        )
    for metric in catalog.metrics:
        text = " ".join(
            (
                metric.name,
                *metric.aliases,
                metric.measure,
                *metric.dimensions,
                *metric.filters,
                metric.grain,
                metric.source_table,
            )
        )
        documents.append(
            {
                "type": "metric",
                "item": metric.as_dict(),
                "label": metric.name,
                "tokens": _phrase_tokens(text),
            }
        )
    return documents


def _lexical_candidates(
    catalog: SemanticCatalog,
    phrase: str,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return fail-closed lexical suggestions for non-exact semantic lookups."""

    query_tokens = set(_phrase_tokens(phrase))
    if not query_tokens:
        return []
    documents = _semantic_item_documents(catalog)
    document_count = len(documents)
    if document_count == 0:
        return []

    document_frequency: dict[str, int] = {}
    for document in documents:
        for token in set(document["tokens"]):
            document_frequency[token] = document_frequency.get(token, 0) + 1

    candidates: list[dict[str, Any]] = []
    for document in documents:
        tokens = tuple(document["tokens"])
        matched_terms = tuple(
            token for token in sorted(query_tokens) if token in set(tokens)
        )
        if not matched_terms:
            continue
        token_count = max(len(tokens), 1)
        score = 0.0
        for token in matched_terms:
            term_frequency = tokens.count(token) / token_count
            inverse_frequency = log((document_count + 1) / (document_frequency[token] + 0.5))
            score += term_frequency * max(inverse_frequency, 0.0)
        coverage = len(matched_terms) / max(len(query_tokens), 1)
        score = round(score + coverage, 6)
        if score <= 0:
            continue
        candidates.append(
            {
                "type": document["type"],
                "item": document["item"],
                "score": score,
                "matched_terms": list(matched_terms),
                "reason": "lexical_overlap",
            }
        )
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:limit]
