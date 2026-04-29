"""Policy-gated Matrix widget proposal and state-event contracts.

Agents do not write widget room state directly. They propose a widget/app
surface, policy evaluates URLs/resources, a user grants approval, and only then
can the bridge create a Matrix state-event draft.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from agent.mcp_gateway.policy import McpServerConfig, evaluate_resource_fetch_policy

WidgetLifecycleStatus = Literal["proposed", "approved", "denied", "revoked", "expired"]

_STATE_KEY_RE = re.compile(r"[^a-zA-Z0-9_.=-]+")


@dataclass(frozen=True)
class MatrixWidgetHostPolicy:
    allowed_origins: tuple[str, ...] = ()
    allowed_resource_prefixes: tuple[str, ...] = ()
    allowed_permissions: tuple[str, ...] = ("read_room",)
    default_required_power_level: int = 50
    event_type: str = "m.widget"
    legacy_event_type: str = "im.vector.modular.widgets"
    sandbox_flags: tuple[str, ...] = ("allow-scripts", "allow-forms", "allow-popups")
    frame_src: tuple[str, ...] = ("'self'",)


@dataclass(frozen=True)
class MatrixWidgetProposal:
    proposal_id: str
    room_id: str
    title: str
    url: str
    requester_user_id: str
    fallback_text: str = ""
    resource_uri: str = ""
    permissions: tuple[str, ...] = ()
    audit_refs: tuple[str, ...] = ()
    required_power_level: int | None = None
    created_at: str = ""
    expires_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MatrixWidgetApproval:
    proposal_id: str
    status: WidgetLifecycleStatus
    decided_by: str
    audit_ref: str
    decided_at: str
    expires_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MatrixWidgetDecision:
    allowed: bool
    reason: str
    proposal: MatrixWidgetProposal | None = None
    denial_reasons: tuple[str, ...] = ()
    state_event: dict[str, Any] | None = None
    fallback_markdown: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.proposal is not None:
            payload["proposal"] = self.proposal.as_dict()
        return payload


def evaluate_widget_proposal(
    proposal: MatrixWidgetProposal,
    policy: MatrixWidgetHostPolicy,
    *,
    mcp_server: McpServerConfig | None = None,
    now: datetime | None = None,
) -> MatrixWidgetDecision:
    """Evaluate a widget proposal without mutating Matrix room state."""

    reasons: list[str] = []
    if not proposal.proposal_id.strip():
        reasons.append("missing-proposal-id")
    if not proposal.room_id.strip():
        reasons.append("missing-room-id")
    if not proposal.title.strip():
        reasons.append("missing-title")
    url_decision = _evaluate_url(policy, proposal.url)
    if not url_decision["allowed"]:
        reasons.append(str(url_decision["reason"]))
    permissions = set(proposal.permissions)
    disallowed_permissions = sorted(permissions - set(policy.allowed_permissions))
    if disallowed_permissions:
        reasons.append("permission-not-allowed")
    if proposal.resource_uri:
        resource_decision = _evaluate_resource(policy, proposal, mcp_server=mcp_server)
        if not resource_decision["allowed"]:
            reasons.append(str(resource_decision["reason"]))
    if _is_expired(proposal.expires_at, now=now):
        reasons.append("proposal-expired")

    return MatrixWidgetDecision(
        allowed=not reasons,
        reason="proposal-policy-allowed" if not reasons else "proposal-policy-denied",
        proposal=proposal,
        denial_reasons=tuple(reasons),
        fallback_markdown=render_widget_fallback_markdown(proposal, url_allowed=not reasons),
    )


def build_widget_state_event(
    proposal: MatrixWidgetProposal,
    policy: MatrixWidgetHostPolicy,
    approval: MatrixWidgetApproval,
    *,
    actor_power_level: int,
    now: datetime | None = None,
    mcp_server: McpServerConfig | None = None,
) -> MatrixWidgetDecision:
    """Create a Matrix state-event draft only after policy and approval pass."""

    proposal_decision = evaluate_widget_proposal(
        proposal,
        policy,
        mcp_server=mcp_server,
        now=now,
    )
    reasons = list(proposal_decision.denial_reasons)
    if approval.proposal_id != proposal.proposal_id:
        reasons.append("approval-proposal-mismatch")
    if approval.status != "approved":
        reasons.append(f"approval-not-approved:{approval.status}")
    if not approval.audit_ref:
        reasons.append("approval-missing-audit-ref")
    if _is_expired(approval.expires_at, now=now):
        reasons.append("approval-expired")
    required_power = proposal.required_power_level
    if required_power is None:
        required_power = policy.default_required_power_level
    if actor_power_level < required_power:
        reasons.append("room-power-level-too-low")
    if reasons:
        return MatrixWidgetDecision(
            allowed=False,
            reason="state-event-denied",
            proposal=proposal,
            denial_reasons=tuple(reasons),
            fallback_markdown=render_widget_fallback_markdown(proposal, url_allowed=False),
        )

    state_key = _state_key(proposal.proposal_id)
    content = {
        "type": "matrix-widget",
        "name": proposal.title.strip(),
        "url": proposal.url.strip(),
        "creatorUserId": proposal.requester_user_id.strip(),
        "waitForIframeLoad": True,
        "data": {
            "fallback": proposal.fallback_text.strip(),
            "permissions": sorted(set(proposal.permissions)),
            "audit_refs": list(proposal.audit_refs) + [approval.audit_ref],
            "resource_uri": proposal.resource_uri.strip() or None,
        },
    }
    return MatrixWidgetDecision(
        allowed=True,
        reason="state-event-draft-created",
        proposal=proposal,
        state_event={
            "room_id": proposal.room_id,
            "event_type": policy.event_type,
            "legacy_event_type": policy.legacy_event_type,
            "state_key": state_key,
            "content": content,
            "sandbox": {
                "flags": list(policy.sandbox_flags),
                "csp": _csp(policy),
            },
        },
        fallback_markdown=render_widget_fallback_markdown(proposal, url_allowed=True),
    )


def build_widget_revoke_state_event(
    proposal: MatrixWidgetProposal,
    policy: MatrixWidgetHostPolicy,
    *,
    revoked_by: str,
    audit_ref: str,
) -> MatrixWidgetDecision:
    """Create a deterministic revoke draft for an existing widget state key."""

    if not audit_ref:
        return MatrixWidgetDecision(
            allowed=False,
            reason="revoke-denied",
            proposal=proposal,
            denial_reasons=("revoke-missing-audit-ref",),
            fallback_markdown=render_widget_fallback_markdown(proposal, url_allowed=False),
        )
    return MatrixWidgetDecision(
        allowed=True,
        reason="revoke-state-event-draft-created",
        proposal=proposal,
        state_event={
            "room_id": proposal.room_id,
            "event_type": policy.event_type,
            "legacy_event_type": policy.legacy_event_type,
            "state_key": _state_key(proposal.proposal_id),
            "content": {
                "type": "matrix-widget",
                "name": proposal.title.strip(),
                "url": "",
                "data": {
                    "status": "revoked",
                    "revoked_by": revoked_by,
                    "audit_ref": audit_ref,
                },
            },
        },
        fallback_markdown=f"Widget revoked: {proposal.title.strip()}",
    )


def render_widget_fallback_markdown(
    proposal: MatrixWidgetProposal,
    *,
    url_allowed: bool = True,
) -> str:
    """Return a stable chat-safe fallback for clients without widget support."""

    title = _markdown_text(proposal.title.strip() or "Widget")
    fallback = _markdown_text(proposal.fallback_text.strip())
    if url_allowed:
        url = proposal.url.strip()
        if fallback:
            return f"[{title}]({url}) - {fallback}"
        return f"[{title}]({url})"
    if fallback:
        return f"{title} - {fallback}"
    return f"{title} (blocked widget URL)"


def _evaluate_url(
    policy: MatrixWidgetHostPolicy,
    url: str,
) -> dict[str, Any]:
    value = str(url or "").strip()
    if not value:
        return {"allowed": False, "reason": "missing-widget-url"}
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"}:
        return {"allowed": False, "reason": "widget-url-scheme-not-allowed"}
    origin = _origin(value)
    if not origin:
        return {"allowed": False, "reason": "missing-widget-origin"}
    if origin not in policy.allowed_origins:
        return {"allowed": False, "reason": "widget-origin-not-allowed"}
    return {"allowed": True, "reason": "widget-url-allowed", "origin": origin}


def _evaluate_resource(
    policy: MatrixWidgetHostPolicy,
    proposal: MatrixWidgetProposal,
    *,
    mcp_server: McpServerConfig | None,
) -> dict[str, Any]:
    if mcp_server is not None:
        return evaluate_resource_fetch_policy(
            mcp_server,
            resource_uri=proposal.resource_uri,
            purpose="matrix-widget",
        )
    if any(
        proposal.resource_uri == prefix
        or proposal.resource_uri.startswith(f"{prefix.rstrip('/')}/")
        for prefix in policy.allowed_resource_prefixes
    ):
        return {"allowed": True, "reason": "resource-prefix-allowed"}
    return {"allowed": False, "reason": "resource-prefix-not-allowed"}


def _origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        return ""
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{parsed.hostname.lower()}{port}"


def _state_key(value: str) -> str:
    normalized = _STATE_KEY_RE.sub("_", value.strip())
    return normalized.strip("_") or "matrix-widget"


def _is_expired(value: str, *, now: datetime | None) -> bool:
    if not value:
        return False
    try:
        expires_at = datetime.fromisoformat(value)
    except ValueError:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    timestamp = now or datetime.now(UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return expires_at <= timestamp


def _markdown_text(value: str) -> str:
    return value.replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)")


def _csp(policy: MatrixWidgetHostPolicy) -> str:
    frame_src = " ".join(policy.frame_src + policy.allowed_origins)
    return f"default-src 'none'; frame-src {frame_src}; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'"
