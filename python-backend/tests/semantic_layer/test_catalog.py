from __future__ import annotations

from semantic_layer.catalog import (
    DEFAULT_SEMANTIC_CATALOG,
    PermissionContext,
    SemanticCatalog,
    SemanticMetric,
    SemanticTerm,
    lookup_phrase,
    plan_metric_query,
    propose_correction,
    review_correction,
    validate_catalog,
)


def test_default_catalog_validates():
    result = validate_catalog(DEFAULT_SEMANTIC_CATALOG)

    assert result["passed"] is True
    assert result["failures"] == []


def test_alias_collision_is_ambiguous():
    catalog = SemanticCatalog(
        terms=(
            SemanticTerm(term_id="risk_term", name="Risk"),
            SemanticTerm(term_id="risk_claim", name="Claim risk", aliases=("risk",)),
        )
    )

    result = validate_catalog(catalog)

    assert result["passed"] is False
    assert any(item.startswith("ambiguous-alias:risk") for item in result["failures"])
    lookup = lookup_phrase(catalog, "risk")
    assert lookup["ambiguous"] is True


def test_metric_plan_filters_missing_tenant_context():
    result = plan_metric_query(
        DEFAULT_SEMANTIC_CATALOG,
        "agent_tool_success_rate",
        PermissionContext(user_id="alice"),
    )

    assert result["allowed"] is False
    assert result["reason"] == "missing-tenant-context"


def test_metric_plan_returns_contract_not_raw_sql():
    result = plan_metric_query(
        DEFAULT_SEMANTIC_CATALOG,
        "agent_tool_success_rate",
        PermissionContext(user_id="alice", tenant_id="tenant-a"),
    )

    assert result["allowed"] is True
    assert result["raw_sql_allowed"] is False
    assert result["sql"] is None
    assert result["semantic_contract"]["source_table"] == "agent.audit_events"


def test_admin_metric_requires_admin_role():
    catalog = SemanticCatalog(
        metrics=(
            SemanticMetric(
                metric_id="admin_metric",
                name="Admin metric",
                measure="count(*)",
                permission_scope="admin",
            ),
        )
    )

    denied = plan_metric_query(catalog, "admin_metric", PermissionContext())
    allowed = plan_metric_query(
        catalog,
        "admin_metric",
        PermissionContext(user_id="root", roles=("admin",)),
    )

    assert denied["allowed"] is False
    assert denied["reason"] == "admin-role-required"
    assert allowed["allowed"] is True


def test_correction_proposal_review_flow():
    proposal = propose_correction(
        target_type="metric",
        target_id="retrieval_pass_rate",
        proposed_by="evaluator",
        rationale="Clarify split handling.",
        patch={"freshness_sla": "per-run"},
    )

    reviewed = review_correction(
        proposal,
        decision="accepted",
        reviewed_by="semantic-owner",
    )

    assert proposal.status == "proposed"
    assert reviewed.status == "accepted"
    assert reviewed.reviewed_by == "semantic-owner"
    assert reviewed.reviewed_at
