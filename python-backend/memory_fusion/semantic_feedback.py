"""Memory-derived semantic correction proposals.

Personal memory may suggest a semantic correction, but it must not become
catalog truth without review.
"""

from __future__ import annotations

from typing import Any, Literal

from memory_fusion.evidence_trace import ensure_memory_trace_metadata
from semantic_layer.catalog import (
    DEFAULT_SEMANTIC_CATALOG,
    CorrectionProposal,
    SemanticCatalog,
    propose_correction,
)


def propose_semantic_correction_from_memory(
    *,
    target_type: Literal["term", "metric"],
    target_id: str,
    proposed_by: str,
    rationale: str,
    patch: dict[str, Any] | None = None,
    memory_unit_id: str = "",
    evidence_ref: str = "",
    source_status: str = "",
    raw_evidence_ref: str = "",
    operation_log_id: str = "",
    diff_ref: str = "",
    catalog: SemanticCatalog = DEFAULT_SEMANTIC_CATALOG,
) -> dict[str, Any]:
    """Create a review-only semantic correction proposal from memory evidence."""

    if not _target_exists(catalog, target_type, target_id):
        return {
            "accepted": False,
            "reason": "semantic-target-not-found",
            "catalog_mutated": False,
            "review_required": True,
        }

    trace = ensure_memory_trace_metadata(
        _drop_blank(
            {
                "memory_unit_id": memory_unit_id,
                "source_ref": evidence_ref,
                "source_status": source_status,
                "raw_evidence_ref": raw_evidence_ref,
                "operation_log_id": operation_log_id,
                "diff_ref": diff_ref,
            }
        ),
        route="semantic_feedback",
        action="semantic_correction",
    )
    if trace.get("source_status") == "unreferenced":
        return {
            "accepted": False,
            "reason": "memory-feedback-evidence-required",
            "catalog_mutated": False,
            "review_required": True,
        }

    feedback_evidence = _feedback_evidence(trace)
    proposal = propose_correction(
        target_type=target_type,
        target_id=target_id,
        proposed_by=proposed_by,
        rationale=rationale,
        patch={
            **dict(patch or {}),
            "_feedback_source": "memory_fusion",
            "_feedback_evidence": feedback_evidence,
        },
    )
    return {
        "accepted": True,
        "proposal": proposal,
        "feedback_evidence": feedback_evidence,
        "catalog_mutated": False,
        "review_required": True,
    }


def proposal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert a feedback result into API-safe dicts."""

    proposal = payload.get("proposal")
    return {
        **payload,
        "proposal": (
            proposal.as_dict() if isinstance(proposal, CorrectionProposal) else proposal
        ),
    }


def _target_exists(
    catalog: SemanticCatalog,
    target_type: Literal["term", "metric"],
    target_id: str,
) -> bool:
    if target_type == "term":
        return any(term.term_id == target_id for term in catalog.terms)
    return any(metric.metric_id == target_id for metric in catalog.metrics)


def _feedback_evidence(trace: dict[str, Any]) -> dict[str, str]:
    keys = (
        "memory_unit_id",
        "source_status",
        "raw_evidence_ref",
        "operation_log_id",
        "diff_ref",
    )
    return {
        key: str(trace.get(key) or "")
        for key in keys
        if str(trace.get(key) or "").strip()
    }


def _drop_blank(metadata: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in metadata.items() if str(value).strip()}
