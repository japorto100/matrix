"""Control Surface - read-only semantic catalog."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from semantic_layer.catalog import (
    DEFAULT_SEMANTIC_CATALOG,
    CorrectionProposal,
    PermissionContext,
    lookup_phrase,
    plan_metric_query,
    propose_correction,
    review_correction,
    validate_catalog,
)

router = APIRouter(tags=["control", "semantic"])
_CORRECTION_PROPOSALS: dict[str, CorrectionProposal] = {}


class SemanticCorrectionRequest(BaseModel):
    target_type: Literal["term", "metric"]
    target_id: str = Field(min_length=1)
    proposed_by: str = Field(default="agent", min_length=1)
    rationale: str = Field(min_length=1)
    patch: dict = Field(default_factory=dict)


class SemanticCorrectionReviewRequest(BaseModel):
    decision: Literal["accepted", "rejected"]
    reviewed_by: str = Field(min_length=1)


@router.get("/semantic/catalog")
async def semantic_catalog() -> dict:
    catalog = DEFAULT_SEMANTIC_CATALOG
    return {
        "catalog": catalog.as_dict(),
        "validation": validate_catalog(catalog),
    }


@router.get("/semantic/lookup")
async def semantic_lookup(phrase: str = Query(..., min_length=1)) -> dict:
    return lookup_phrase(DEFAULT_SEMANTIC_CATALOG, phrase)


@router.get("/semantic/metrics/{metric_id}/plan")
async def semantic_metric_plan(
    metric_id: str,
    user_id: str = "",
    tenant_id: str = "",
    role: list[str] | None = None,
) -> dict:
    return plan_metric_query(
        DEFAULT_SEMANTIC_CATALOG,
        metric_id,
        PermissionContext(
            user_id=user_id, tenant_id=tenant_id, roles=tuple(role or ())
        ),
    )


def _target_exists(target_type: Literal["term", "metric"], target_id: str) -> bool:
    if target_type == "term":
        return any(term.term_id == target_id for term in DEFAULT_SEMANTIC_CATALOG.terms)
    return any(metric.metric_id == target_id for metric in DEFAULT_SEMANTIC_CATALOG.metrics)


@router.post("/semantic/corrections")
async def semantic_correction_propose(request: SemanticCorrectionRequest) -> dict:
    if not _target_exists(request.target_type, request.target_id):
        raise HTTPException(status_code=404, detail="semantic-target-not-found")
    proposal = propose_correction(
        target_type=request.target_type,
        target_id=request.target_id,
        proposed_by=request.proposed_by,
        rationale=request.rationale,
        patch=request.patch,
    )
    _CORRECTION_PROPOSALS[proposal.proposal_id] = proposal
    return {
        "proposal": proposal.as_dict(),
        "catalog_mutated": False,
        "review_required": True,
    }


@router.get("/semantic/corrections")
async def semantic_correction_list(status: str = "") -> dict:
    proposals = list(_CORRECTION_PROPOSALS.values())
    if status:
        proposals = [proposal for proposal in proposals if proposal.status == status]
    return {"proposals": [proposal.as_dict() for proposal in proposals]}


@router.post("/semantic/corrections/{proposal_id}/review")
async def semantic_correction_review(
    proposal_id: str,
    request: SemanticCorrectionReviewRequest,
) -> dict:
    proposal = _CORRECTION_PROPOSALS.get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="semantic-proposal-not-found")
    reviewed = review_correction(
        proposal,
        decision=request.decision,
        reviewed_by=request.reviewed_by,
    )
    _CORRECTION_PROPOSALS[proposal_id] = reviewed
    return {
        "proposal": reviewed.as_dict(),
        "catalog_mutated": False,
        "review_recorded": True,
    }
