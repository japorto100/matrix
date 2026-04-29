"""Deterministic Meta-Harness lane for Matrix widget host policy."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from agent.matrix_widgets.policy import (
    MatrixWidgetApproval,
    MatrixWidgetHostPolicy,
    MatrixWidgetProposal,
    build_widget_state_event,
    evaluate_widget_proposal,
)
from agent.mcp_gateway.policy import McpServerConfig

DEFAULT_RUN_ID = "run-matrix-widget-policy"


def run_matrix_widget_policy_scenarios(
    *,
    run_id: str = DEFAULT_RUN_ID,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """Run provider-free Matrix widget proposal scenarios and write artifacts."""

    data_root = data_dir or Path(__file__).resolve().parents[2] / "data" / "meta_harness"
    run_dir = data_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        _approved_state_event_scenario(),
        _unsafe_url_blocked_scenario(),
        _mcp_resource_handoff_blocked_scenario(),
    ]
    passed = all(scenario["passed"] for scenario in scenarios)
    summary = {
        "run_id": run_id,
        "kind": "matrix_widget_policy",
        "feature_id": "030",
        "created_at": datetime.now(UTC).isoformat(),
        "passed": passed,
        "scenario_count": len(scenarios),
        "passed_count": sum(1 for scenario in scenarios if scenario["passed"]),
        "scenarios": scenarios,
    }
    _write_json(run_dir / "matrix_widget_policy.json", summary)
    _write_json(
        run_dir / "run.json",
        {
            "run_id": run_id,
            "kind": "matrix_widget_policy",
            "feature_id": "030",
            "frontend_required": False,
            "external_mcp_required": False,
            "provider_calls_required": False,
            "created_at": summary["created_at"],
        },
    )
    return {**summary, "artifact_path": str(run_dir / "matrix_widget_policy.json")}


def _approved_state_event_scenario() -> dict[str, Any]:
    now = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
    policy = MatrixWidgetHostPolicy(allowed_origins=("https://widgets.example",))
    proposal = MatrixWidgetProposal(
        proposal_id="portfolio-widget",
        room_id="!room:example",
        title="Portfolio Widget",
        url="https://widgets.example/portfolio",
        requester_user_id="@agent:example",
        fallback_text="Open portfolio widget",
        permissions=("read_room",),
        audit_refs=("audit-proposal",),
        expires_at=(now + timedelta(minutes=5)).isoformat(),
    )
    approval = MatrixWidgetApproval(
        proposal_id=proposal.proposal_id,
        status="approved",
        decided_by="@alice:example",
        audit_ref="audit-approval",
        decided_at=now.isoformat(),
        expires_at=(now + timedelta(minutes=5)).isoformat(),
    )
    decision = build_widget_state_event(
        proposal,
        policy,
        approval,
        actor_power_level=50,
        now=now,
    )
    failures = []
    if not decision.allowed:
        failures.append("approved widget did not produce state event")
    if not decision.state_event:
        failures.append("missing state event")
    elif decision.state_event["event_type"] != "m.widget":
        failures.append("wrong event type")
    return {
        "id": "matrix-widget-approved-state-event",
        "passed": not failures,
        "failures": failures,
        "decision": decision.as_dict(),
    }


def _unsafe_url_blocked_scenario() -> dict[str, Any]:
    policy = MatrixWidgetHostPolicy(allowed_origins=("https://widgets.example",))
    proposal = MatrixWidgetProposal(
        proposal_id="unsafe",
        room_id="!room:example",
        title="Unsafe Widget",
        url="javascript:alert(1)",
        requester_user_id="@agent:example",
        fallback_text="Blocked unsafe widget",
    )
    decision = evaluate_widget_proposal(proposal, policy)
    failures = []
    if decision.allowed:
        failures.append("unsafe widget URL was allowed")
    if "widget-url-scheme-not-allowed" not in decision.denial_reasons:
        failures.append("missing unsafe scheme denial")
    return {
        "id": "matrix-widget-unsafe-url-blocked",
        "passed": not failures,
        "failures": failures,
        "decision": decision.as_dict(),
    }


def _mcp_resource_handoff_blocked_scenario() -> dict[str, Any]:
    policy = MatrixWidgetHostPolicy(allowed_origins=("https://widgets.example",))
    proposal = MatrixWidgetProposal(
        proposal_id="resource",
        room_id="!room:example",
        title="Resource Widget",
        url="https://widgets.example/resource",
        requester_user_id="@agent:example",
        resource_uri="https://blocked.example/private",
    )
    server = McpServerConfig(
        server_id="external",
        transport="streamable-http",
        enabled=True,
        denylisted_domains=("blocked.example",),
    )
    decision = evaluate_widget_proposal(proposal, policy, mcp_server=server)
    failures = []
    if decision.allowed:
        failures.append("denied Feature 024 resource was allowed into widget host")
    if "domain-denylisted" not in decision.denial_reasons:
        failures.append("missing Feature 024 resource denial")
    return {
        "id": "matrix-widget-mcp-resource-policy",
        "passed": not failures,
        "failures": failures,
        "decision": decision.as_dict(),
    }


def _write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
