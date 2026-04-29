from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agent.matrix_widgets.policy import (
    MatrixWidgetApproval,
    MatrixWidgetHostPolicy,
    MatrixWidgetProposal,
    build_report_artifact_widget_proposal,
    build_widget_revoke_state_event,
    build_widget_state_event,
    evaluate_widget_proposal,
    render_widget_fallback_markdown,
)
from agent.mcp_gateway.policy import McpServerConfig


def test_widget_proposal_requires_allowed_origin_and_safe_scheme() -> None:
    policy = MatrixWidgetHostPolicy(allowed_origins=("https://widgets.example",))
    blocked_scheme = MatrixWidgetProposal(
        proposal_id="w1",
        room_id="!room:example",
        title="Bad Widget",
        url="javascript:alert(1)",
        requester_user_id="@agent:example",
    )
    blocked_origin = MatrixWidgetProposal(
        proposal_id="w2",
        room_id="!room:example",
        title="Other Widget",
        url="https://other.example/widget",
        requester_user_id="@agent:example",
    )
    allowed = MatrixWidgetProposal(
        proposal_id="w3",
        room_id="!room:example",
        title="Safe Widget",
        url="https://widgets.example/app",
        requester_user_id="@agent:example",
    )

    assert evaluate_widget_proposal(blocked_scheme, policy).denial_reasons == (
        "widget-url-scheme-not-allowed",
    )
    assert evaluate_widget_proposal(blocked_origin, policy).denial_reasons == (
        "widget-origin-not-allowed",
    )
    assert evaluate_widget_proposal(allowed, policy).allowed is True


def test_widget_state_event_requires_approval_and_room_power_level() -> None:
    now = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
    policy = MatrixWidgetHostPolicy(allowed_origins=("https://widgets.example",))
    proposal = MatrixWidgetProposal(
        proposal_id="matrix summary",
        room_id="!room:example",
        title="Matrix Summary",
        url="https://widgets.example/summary",
        requester_user_id="@agent:example",
        fallback_text="Open summary",
        permissions=("read_room",),
        audit_refs=("audit-proposal",),
        expires_at=(now + timedelta(minutes=5)).isoformat(),
    )
    approval = MatrixWidgetApproval(
        proposal_id="matrix summary",
        status="approved",
        decided_by="@alice:example",
        audit_ref="audit-approval",
        decided_at=now.isoformat(),
        expires_at=(now + timedelta(minutes=5)).isoformat(),
    )

    denied = build_widget_state_event(
        proposal,
        policy,
        approval,
        actor_power_level=49,
        now=now,
    )
    assert denied.allowed is False
    assert "room-power-level-too-low" in denied.denial_reasons

    allowed = build_widget_state_event(
        proposal,
        policy,
        approval,
        actor_power_level=50,
        now=now,
    )
    assert allowed.allowed is True
    assert allowed.state_event is not None
    assert allowed.state_event["event_type"] == "m.widget"
    assert allowed.state_event["legacy_event_type"] == "im.vector.modular.widgets"
    assert allowed.state_event["state_key"] == "matrix_summary"
    assert allowed.state_event["content"]["data"]["audit_refs"] == [
        "audit-proposal",
        "audit-approval",
    ]
    assert "https://widgets.example" in allowed.state_event["sandbox"]["csp"]


def test_widget_resource_handoff_uses_feature_024_policy() -> None:
    policy = MatrixWidgetHostPolicy(allowed_origins=("https://widgets.example",))
    proposal = MatrixWidgetProposal(
        proposal_id="w1",
        room_id="!room:example",
        title="Blocked Resource",
        url="https://widgets.example/app",
        requester_user_id="@agent:example",
        resource_uri="https://blocked.example/resource",
    )
    server = McpServerConfig(
        server_id="external",
        transport="streamable-http",
        enabled=True,
        denylisted_domains=("blocked.example",),
    )

    decision = evaluate_widget_proposal(proposal, policy, mcp_server=server)

    assert decision.allowed is False
    assert "domain-denylisted" in decision.denial_reasons


def test_widget_revoke_requires_audit_ref() -> None:
    policy = MatrixWidgetHostPolicy(allowed_origins=("https://widgets.example",))
    proposal = MatrixWidgetProposal(
        proposal_id="w1",
        room_id="!room:example",
        title="Safe Widget",
        url="https://widgets.example/app",
        requester_user_id="@agent:example",
    )

    denied = build_widget_revoke_state_event(
        proposal,
        policy,
        revoked_by="@alice:example",
        audit_ref="",
    )
    allowed = build_widget_revoke_state_event(
        proposal,
        policy,
        revoked_by="@alice:example",
        audit_ref="audit-revoke",
    )

    assert denied.allowed is False
    assert allowed.allowed is True
    assert allowed.state_event is not None
    assert allowed.state_event["content"]["data"]["status"] == "revoked"


def test_widget_fallback_markdown_escapes_title() -> None:
    proposal = MatrixWidgetProposal(
        proposal_id="w1",
        room_id="!room:example",
        title="[Danger](x)",
        url="https://widgets.example/app",
        requester_user_id="@agent:example",
        fallback_text="open",
    )

    markdown = render_widget_fallback_markdown(proposal)

    assert markdown == "[\\[Danger\\]\\(x\\)](https://widgets.example/app) - open"


def test_report_artifact_widget_proposal_carries_manifest_metadata() -> None:
    now = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
    policy = MatrixWidgetHostPolicy(
        allowed_origins=("https://widgets.example",),
        allowed_resource_prefixes=("report://matrix/",),
    )
    proposal = build_report_artifact_widget_proposal(
        report_id="risk-brief",
        title="Risk Brief",
        output_path="reports/risk-brief/report.html",
        manifest_path="reports/risk-brief/manifest.json",
        renderer="markdown-fallback",
        room_id="!room:example",
        requester_user_id="@agent:example",
        widget_url="https://widgets.example/reports/risk-brief",
        audit_refs=("audit-report-build",),
    )
    approval = MatrixWidgetApproval(
        proposal_id=proposal.proposal_id,
        status="approved",
        decided_by="@alice:example",
        audit_ref="audit-report-approval",
        decided_at=now.isoformat(),
    )

    decision = build_widget_state_event(
        proposal,
        policy,
        approval,
        actor_power_level=50,
        now=now,
    )

    assert decision.allowed is True
    assert decision.state_event is not None
    data = decision.state_event["content"]["data"]
    assert data["report_manifest_id"] == "reports/risk-brief/manifest.json"
    assert data["report_output_path"] == "reports/risk-brief/report.html"
    assert data["report_renderer"] == "markdown-fallback"
    assert data["audit_refs"] == ["audit-report-build", "audit-report-approval"]
