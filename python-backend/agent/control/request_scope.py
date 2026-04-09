"""Helpers to resolve user/team scope for control routes.

Primary source is forwarded auth headers from Go Gateway. Query params are
accepted only as fallback for local/dev calls.

This is a small abstraction so control routes can be migrated from "user_id
query param everywhere" to "header-first identity" without a big refactor.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request


@dataclass(frozen=True)
class RequestScope:
    """Caller identity resolved for a request."""

    user_id: str
    team_id: str | None
    # Human-readable actor label for audit metadata. For now we default to user_id,
    # but this can be swapped to a stable subject identifier later.
    actor: str


def resolve_user_id(request: Request, fallback_user_id: str | None = None) -> str:
    """Resolve user_id with header-first precedence."""
    header_user = request.headers.get("x-auth-user")
    if header_user:
        return header_user
    if fallback_user_id:
        return fallback_user_id
    return "local"


def resolve_team_id(request: Request, fallback_team_id: str | None = None) -> str | None:
    """Resolve team_id with header-first precedence."""
    header_team = request.headers.get("x-auth-team")
    if header_team:
        return header_team
    return fallback_team_id


def resolve_scope(
    request: Request,
    *,
    requested_user_id: str | None = None,
    requested_team_id: str | None = None,
) -> RequestScope:
    """Resolve RequestScope from headers with optional requested fallbacks.

    Header precedence prevents user_id spoofing via query params when the gateway
    forwards authenticated identity. Query/body can still be used for local dev.
    """
    user_id = resolve_user_id(request, fallback_user_id=requested_user_id)
    team_id = resolve_team_id(request, fallback_team_id=requested_team_id)
    actor = request.headers.get("x-auth-actor") or user_id
    return RequestScope(user_id=user_id, team_id=team_id, actor=actor)


def get_request_scope(
    request: Request,
    *,
    requested_user_id: str | None = None,
    requested_team_id: str | None = None,
) -> RequestScope:
    """Backward-compatible helper for call sites not using Depends()."""
    return resolve_scope(
        request,
        requested_user_id=requested_user_id,
        requested_team_id=requested_team_id,
    )


RequestScopeDep = Depends(resolve_scope)

