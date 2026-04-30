from __future__ import annotations


async def test_semantic_catalog_endpoint_validates_default_catalog():
    from agent.control.semantic import semantic_catalog

    payload = await semantic_catalog()

    assert payload["validation"]["passed"] is True
    assert payload["catalog"]["metrics"]


async def test_semantic_lookup_endpoint_returns_metric():
    from agent.control.semantic import semantic_lookup

    payload = await semantic_lookup("tool success rate")

    assert payload["matched"] is True
    assert payload["matches"][0]["type"] == "metric"


async def test_semantic_metric_plan_endpoint_respects_tenant_scope():
    from agent.control.semantic import semantic_metric_plan

    denied = await semantic_metric_plan("agent_tool_success_rate")
    allowed = await semantic_metric_plan(
        "agent_tool_success_rate",
        user_id="alice",
        tenant_id="tenant-a",
    )

    assert denied["allowed"] is False
    assert allowed["allowed"] is True
    assert allowed["raw_sql_allowed"] is False


async def test_semantic_correction_endpoint_creates_review_proposal():
    from agent.control import semantic

    semantic._CORRECTION_PROPOSALS.clear()

    proposed = await semantic.semantic_correction_propose(
        semantic.SemanticCorrectionRequest(
            target_type="metric",
            target_id="retrieval_pass_rate",
            proposed_by="alice",
            rationale="Clarify benchmark split semantics.",
            patch={"description": "Use holdout split only."},
        )
    )

    proposal_id = proposed["proposal"]["proposal_id"]
    assert proposed["catalog_mutated"] is False
    assert proposed["review_required"] is True
    assert proposed["proposal"]["status"] == "proposed"

    listed = await semantic.semantic_correction_list(status="proposed")
    assert [item["proposal_id"] for item in listed["proposals"]] == [proposal_id]

    reviewed = await semantic.semantic_correction_review(
        proposal_id,
        semantic.SemanticCorrectionReviewRequest(
            decision="accepted",
            reviewed_by="semantic-reviewer",
        ),
    )

    assert reviewed["catalog_mutated"] is False
    assert reviewed["review_recorded"] is True
    assert reviewed["proposal"]["status"] == "accepted"
