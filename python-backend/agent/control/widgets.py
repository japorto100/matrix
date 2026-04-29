"""Control Surface - Matrix widget proposal approval read model."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter

from agent.control.reports import _list_report_artifacts, _report_root
from agent.matrix_widgets.policy import (
    MatrixWidgetHostPolicy,
    build_report_artifact_widget_proposal,
    evaluate_widget_proposal,
)

router = APIRouter(tags=["control", "widgets"])


def _allowed_origins() -> tuple[str, ...]:
    raw = os.environ.get("MATRIX_WIDGET_ALLOWED_ORIGINS", "https://widgets.example")
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


def _widget_base_url() -> str:
    return os.environ.get("MATRIX_WIDGET_APP_BASE_URL", "https://widgets.example").rstrip("/")


def _widget_policy() -> MatrixWidgetHostPolicy:
    return MatrixWidgetHostPolicy(
        allowed_origins=_allowed_origins(),
        allowed_resource_prefixes=("report://matrix/",),
    )


@router.get("/widgets/proposals")
async def list_widget_proposals() -> dict[str, Any]:
    items = _list_widget_proposals(_report_root(), _widget_policy(), _widget_base_url())
    return {
        "items": items,
        "total": len(items),
        "summary": {
            "pending": sum(1 for item in items if item["status"] == "pending"),
            "approved": sum(1 for item in items if item["status"] == "approved"),
            "blocked": sum(1 for item in items if item["status"] == "blocked"),
        },
        "contract": "matrix-widget-approval/v1",
    }


def _list_widget_proposals(
    report_root: Path,
    policy: MatrixWidgetHostPolicy,
    widget_base_url: str,
) -> list[dict[str, Any]]:
    reports = _list_report_artifacts(report_root)
    items = [_proposal_from_report(report, policy, widget_base_url) for report in reports]
    return [item for item in items if item is not None]


def _proposal_from_report(
    report: dict[str, Any],
    policy: MatrixWidgetHostPolicy,
    widget_base_url: str,
) -> dict[str, Any] | None:
    report_id = str(report.get("report_id") or "").strip()
    if not report_id:
        return None

    publication = report.get("matrix_publication") or {}
    room_id = str(publication.get("room_id") or "!pending:matrix.local")
    output_path = _preferred_output_path(report)
    manifest_path = str(report.get("manifest_path") or "")
    renderer = str(report.get("renderer") or "markdown-fallback")
    widget_url = f"{widget_base_url}/reports/{quote(report_id)}"
    audit_refs = tuple(
        ref
        for ref in (
            str(report.get("checksum") or "").strip(),
            str(publication.get("event_id") or "").strip(),
        )
        if ref
    )

    proposal = build_report_artifact_widget_proposal(
        report_id=report_id,
        title=str(report.get("title") or report_id),
        output_path=output_path,
        manifest_path=manifest_path,
        renderer=renderer,
        room_id=room_id,
        requester_user_id=str(report.get("owner") or "@agent:matrix.local"),
        widget_url=widget_url,
        audit_refs=audit_refs,
    )
    decision = evaluate_widget_proposal(proposal, policy)
    validation = report.get("validation") or {}
    publication_status = str(publication.get("status") or "not_published")
    status = _approval_status(
        policy_allowed=decision.allowed,
        validation_passed=bool(validation.get("passed")),
        publication_status=publication_status,
    )
    return {
        "proposal_id": proposal.proposal_id,
        "report_id": report_id,
        "title": proposal.title,
        "room_id": proposal.room_id,
        "requester_user_id": proposal.requester_user_id,
        "url": proposal.url,
        "resource_uri": proposal.resource_uri,
        "status": status,
        "approval_required": status == "pending",
        "can_approve": decision.allowed and status == "pending",
        "can_deny": status == "pending",
        "denial_reasons": list(decision.denial_reasons),
        "fallback_markdown": decision.fallback_markdown,
        "permissions": list(proposal.permissions),
        "audit_refs": list(proposal.audit_refs),
        "report_artifact": {
            "manifest_id": proposal.report_manifest_id,
            "output_path": proposal.report_output_path,
            "renderer": proposal.report_renderer,
        },
        "matrix_publication": publication,
        "validation": validation,
    }


def _preferred_output_path(report: dict[str, Any]) -> str:
    output_files = report.get("output_files") or ()
    for preferred in ("html", "text", "source", "pdf"):
        for item in output_files:
            if isinstance(item, dict) and item.get("kind") == preferred and item.get("path"):
                return str(item["path"])
    return str(report.get("manifest_path") or "")


def _approval_status(
    *,
    policy_allowed: bool,
    validation_passed: bool,
    publication_status: str,
) -> str:
    if not policy_allowed or not validation_passed or publication_status == "blocked":
        return "blocked"
    if publication_status == "published":
        return "approved"
    return "pending"
