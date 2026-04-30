"""Control Surface — Skills Registry (Slice 5 backend).

Wraps agent/skills/loader.py — exposes 3-tier skills (global/team/personal)
via REST. Read-only in Phase 1 except enable/disable toggle.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from agent.control.cache_impact import (
    build_cache_impact,
    cache_impact_runtime_event,
    digest_records,
    stable_digest,
)
from agent.control.request_scope import RequestScope, resolve_scope
from agent.skills.db_state import load_skill_toggle_overrides
from agent.skills.loader import load_skills
from agent.skills.usage_state import record_view, set_pinned, skill_usage_snapshot

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "skills"])


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def _load_enabled_overrides(user_id: str = "local") -> dict[str, bool]:
    """Return {skill_id: enabled} overrides from DB."""
    return load_skill_toggle_overrides(user_id)


def _tenant_id(scope: RequestScope) -> str:
    return str(getattr(scope, "tenant_id", None) or "matrix-local")


def _skill_catalog_digest(
    skills: list[Any],
    *,
    overrides: dict[str, bool] | None = None,
) -> str:
    override_map = overrides or {}
    records: list[dict[str, Any]] = []
    for skill in skills:
        skill_id = f"{skill.tier}:{skill.name}"
        enabled = override_map.get(skill_id, skill.enabled)
        records.append(
            {
                "id": skill_id,
                "name": skill.name,
                "tier": skill.tier,
                "category": skill.category,
                "generation": skill.generation,
                "enabled": bool(enabled),
                "owner": skill.owner,
                "db_id": getattr(skill, "db_id", None),
                "skill_type": getattr(skill, "skill_type", None),
                "api_version": getattr(skill, "api_version", None),
                "content_digest": stable_digest(skill.content or ""),
                "assets_digest": stable_digest(getattr(skill, "assets", {}) or {}),
            }
        )
    records.sort(key=lambda item: str(item.get("id") or ""))
    return digest_records(records)


def _skill_cache_impact(
    *,
    source: str,
    reason: str,
    skills: list[Any],
    scope: RequestScope,
    previous_digest: str | None = None,
    overrides: dict[str, bool] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_cache_impact(
        source=source,
        reason=reason,
        previous_digest=previous_digest,
        next_digest=_skill_catalog_digest(skills, overrides=overrides),
        scope={
            "tenant_id": _tenant_id(scope),
            "team_id": scope.team_id,
            "user_id": scope.user_id,
        },
        details={
            "skill_count": len(skills),
            "enabled_skill_count": sum(
                1
                for skill in skills
                if (overrides or {}).get(f"{skill.tier}:{skill.name}", skill.enabled)
            ),
            **(details or {}),
        },
    )


def _skill_to_dict(skill: Any, idx: int) -> dict[str, Any]:
    skill_id = f"{skill.tier}:{skill.name}"
    usage = skill_usage_snapshot(skill_id)
    return {
        "id": skill_id,
        "name": skill.name,
        "description": skill.description,
        "tier": skill.tier,
        "category": skill.category,
        "generation": skill.generation,
        "enabled": skill.enabled,
        "owner": skill.owner,
        "db_id": getattr(skill, "db_id", None),
        "path": str(skill.path),
        "body_preview": skill.content[:400] if skill.content else "",
        "usage": {
            "use_count": int(usage.get("use_count") or 0),
            "view_count": int(usage.get("view_count") or 0),
            "last_used_at": usage.get("last_used_at"),
            "last_viewed_at": usage.get("last_viewed_at"),
        },
        "pinned": bool(usage.get("pinned")),
        "lifecycle_state": usage.get("state", "active"),
        "source": (
            "db"
            if getattr(skill, "db_id", None)
            else (
                "builtin"
                if skill.tier == "global"
                else ("github" if skill.tier == "team" else "local")
            )
        ),
    }


@router.get("/skills")
async def list_skills_endpoint(
    tier: str | None = None,
    scope: RequestScope = Depends(resolve_scope),
) -> dict[str, Any]:
    """List all skills (or filter by tier)."""
    try:
        skills = load_skills(user_id=scope.user_id, team_id=scope.team_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("load_skills failed: %s", e)
        skills = []

    items = [_skill_to_dict(s, i) for i, s in enumerate(skills)]
    overrides = _load_enabled_overrides(scope.user_id)
    for item in items:
        if item["id"] in overrides:
            item["enabled"] = overrides[item["id"]]
    if tier:
        if tier not in {"global", "team", "personal"}:
            raise HTTPException(
                status_code=400, detail="tier must be global|team|personal"
            )
        items = [i for i in items if i["tier"] == tier]
    return {"items": items, "total": len(items)}


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str, user_id: str = "local") -> dict[str, Any]:
    try:
        skills = load_skills(user_id=user_id, team_id=None)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"load_skills: {e}") from e

    for s in skills:
        sid = f"{s.tier}:{s.name}"
        if sid == skill_id:
            record_view(sid)
            d = _skill_to_dict(s, 0)
            overrides = _load_enabled_overrides(user_id)
            if sid in overrides:
                d["enabled"] = overrides[sid]
            d["body"] = s.content  # full body, not just preview
            return d
    raise HTTPException(status_code=404, detail="Skill not found")


class PatchSkillRequest(BaseModel):
    enabled: bool


class PinSkillRequest(BaseModel):
    pinned: bool


class ImportSkillRequest(BaseModel):
    github_url: str
    name: str | None = None
    description: str | None = None
    tier: str = "personal"


class ReloadSkillsRequest(BaseModel):
    confirm: bool = False
    previous_digest: str | None = None
    session_id: str = ""
    thread_id: str = ""


@router.post("/skills/reload")
async def reload_skills(
    req: ReloadSkillsRequest,
    request: Request,
    scope: RequestScope = Depends(resolve_scope),
) -> dict[str, Any]:
    """Preview or confirm a next-turn skill reload and cache-impact metadata."""

    try:
        skills = load_skills(user_id=scope.user_id, team_id=scope.team_id)
        overrides = _load_enabled_overrides(scope.user_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"load_skills: {e}") from e

    impact = _skill_cache_impact(
        source="skill_reload",
        reason="skill_catalog_reloaded",
        previous_digest=req.previous_digest,
        skills=skills,
        overrides=overrides,
        scope=scope,
        details={"reload_mode": "next_turn_rebind"},
    )
    runtime_event = cache_impact_runtime_event(
        impact,
        session_id=req.session_id,
        thread_id=req.thread_id,
    )
    if not req.confirm:
        return {
            "status": "confirmation_required",
            "cache_impact": impact,
            "runtime_events": [runtime_event],
            "confirm_required": impact["action"] == "rebind_required",
        }

    try:
        from agent.audit.logger import AuditAction, audit_log

        await audit_log(
            action=AuditAction.ROUTE_DECISION,
            user_id=scope.user_id,
            session_id=req.session_id,
            thread_id=req.thread_id,
            metadata={
                "control_action": "skill_reload",
                "cache_impact": impact,
                "runtime_events": [runtime_event],
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("skill reload audit failed: %s", exc)

    return {
        "status": "reloaded",
        "cache_impact": impact,
        "runtime_events": [runtime_event],
    }


@router.patch("/skills/{skill_id}")
async def patch_skill(
    skill_id: str,
    req: PatchSkillRequest,
    request: Request,
    scope: RequestScope = Depends(resolve_scope),
) -> dict[str, Any]:
    """Enable/disable a skill (bounded-write, persisted to DB)."""
    try:
        skills = load_skills(user_id=scope.user_id, team_id=scope.team_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"load_skills: {e}") from e

    if skill_id not in {f"{s.tier}:{s.name}" for s in skills}:
        raise HTTPException(status_code=404, detail="Skill not found")

    before_overrides = _load_enabled_overrides(scope.user_id)
    before_digest = _skill_catalog_digest(skills, overrides=before_overrides)
    after_overrides = {**before_overrides, skill_id: req.enabled}
    impact = _skill_cache_impact(
        source="skill_toggle",
        reason="skill_enabled_state_changed",
        previous_digest=before_digest,
        skills=skills,
        overrides=after_overrides,
        scope=scope,
        details={"skill_id": skill_id, "enabled": req.enabled},
    )
    runtime_event = cache_impact_runtime_event(impact)

    now = datetime.now(UTC)
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            # Resolve tier:name → agent_skills UUID for user_skill_preferences FK
            skill_uuid_row = conn.execute(
                """
                SELECT id FROM agent.agent_skills
                WHERE tier || ':' || name = %s AND enabled = true
                LIMIT 1
                """,
                (skill_id,),
            ).fetchone()

            if skill_uuid_row:
                conn.execute(
                    """
                    INSERT INTO agent.user_skill_preferences
                        (user_id, skill_id, disabled)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, skill_id)
                    DO UPDATE SET disabled = EXCLUDED.disabled
                    """,
                    (scope.user_id, skill_uuid_row[0], not req.enabled),
                )
            else:
                # Fallback to legacy skills_state if skill not in DB
                conn.execute(
                    """
                    INSERT INTO agent.skills_state
                        (skill_id, user_id, enabled, updated_by, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (skill_id, user_id)
                    DO UPDATE SET
                        enabled = EXCLUDED.enabled,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (skill_id, scope.user_id, req.enabled, scope.actor, now),
                )
            conn.execute(
                """
                INSERT INTO agent.audit_events
                    (timestamp, action, user_id, success, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    now,
                    "SKILL_TOGGLE",
                    scope.user_id,
                    True,
                    json.dumps(
                        {
                            "skill_id": skill_id,
                            "enabled": req.enabled,
                            "updated_by": scope.actor,
                            "team_id": scope.team_id,
                            "tenant_id": _tenant_id(scope),
                            "cache_impact": impact,
                            "runtime_events": [runtime_event],
                        }
                    ),
                ),
            )
    except Exception as e:  # noqa: BLE001
        logger.exception("patch_skill failed")
        raise HTTPException(status_code=500, detail=f"patch: {e}") from e

    return {
        "status": "updated",
        "skill_id": skill_id,
        "enabled": req.enabled,
        "updated_by": scope.actor,
        "updated_at": now.isoformat(),
    }


@router.patch("/skills/{skill_id}/pin")
async def pin_skill(
    skill_id: str,
    req: PinSkillRequest,
    request: Request,
    scope: RequestScope = Depends(resolve_scope),
) -> dict[str, Any]:
    """Pin/unpin a skill so imports and archives cannot silently overwrite it."""
    try:
        skills = load_skills(user_id=scope.user_id, team_id=scope.team_id)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"load_skills: {e}") from e

    if skill_id not in {f"{s.tier}:{s.name}" for s in skills}:
        raise HTTPException(status_code=404, detail="Skill not found")

    usage = set_pinned(skill_id, req.pinned)
    now = datetime.now(UTC)
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                """
                INSERT INTO agent.audit_events
                    (timestamp, action, user_id, success, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    now,
                    "SKILL_PIN",
                    scope.user_id,
                    True,
                    json.dumps(
                        {
                            "skill_id": skill_id,
                            "pinned": req.pinned,
                            "updated_by": scope.actor,
                            "team_id": scope.team_id,
                            "tenant_id": _tenant_id(scope),
                        }
                    ),
                ),
            )
    except Exception:  # noqa: BLE001
        logger.exception("skill pin audit write failed — continuing")

    return {
        "status": "updated",
        "skill_id": skill_id,
        "pinned": bool(usage.get("pinned")),
        "updated_by": scope.actor,
        "updated_at": usage.get("updated_at"),
    }


@router.post("/skills/import")
async def import_skill_from_github(
    req: ImportSkillRequest,
    request: Request,
    scope: RequestScope = Depends(resolve_scope),
) -> dict[str, Any]:
    """Import skills from GitHub — skills_guard pre-scan + HITL on dangerous.

    Wires the ``agent.skills.importer.import_from_github()`` implementation
    (which includes the skills_guard two-pass scan) so the SkillsGuardDrawer
    UI can actually fire on dangerous verdict. Before this wiring, the
    endpoint only wrote a SKILL_IMPORT_REQUESTED audit row and returned
    ``{"status": "queued"}`` — the guard + HITL path was dead code.

    Returns 422 with ``{"success": false, "rejected": [...],
    "suggested_action": "hitl_confirm"}`` when the scan classifies any
    candidate as ``dangerous`` — the frontend's ``extractSkillsGuardVerdict``
    picks that up and opens the drawer. Returns 200 with ``success=true``
    on clean import.
    """
    if not req.github_url.startswith(("https://github.com/", "http://github.com/")):
        raise HTTPException(status_code=400, detail="github_url must be a GitHub URL")
    if req.tier not in {"team", "personal"}:
        raise HTTPException(status_code=400, detail="tier must be team|personal")

    now = datetime.now(UTC)
    try:
        before_skills = load_skills(user_id=scope.user_id, team_id=scope.team_id)
        before_overrides = _load_enabled_overrides(scope.user_id)
        before_digest = _skill_catalog_digest(before_skills, overrides=before_overrides)
    except Exception:  # noqa: BLE001
        before_digest = None

    # Audit the request attempt regardless of outcome (for ops visibility)
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                """
                INSERT INTO agent.audit_events
                    (timestamp, action, user_id, success, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    now,
                    "SKILL_IMPORT_REQUESTED",
                    scope.user_id,
                    True,
                    json.dumps(
                        {
                            "github_url": req.github_url,
                            "tier": req.tier,
                            "name": req.name,
                            "description": req.description,
                            "updated_by": scope.actor,
                            "team_id": scope.team_id,
                            "tenant_id": _tenant_id(scope),
                        }
                    ),
                ),
            )
    except Exception:  # noqa: BLE001
        logger.exception("skill import audit write failed — continuing")

    # Run the actual import (clone + two-pass scan + install)
    from agent.skills.importer import import_from_github

    try:
        result = await import_from_github(
            repo_url=req.github_url,
            target_tier=req.tier,
            target_owner=scope.user_id if req.tier == "personal" else scope.team_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("skill import failed")
        raise HTTPException(status_code=500, detail=f"import: {e}") from e

    # HITL gate: if the scan flagged anything dangerous, propagate the
    # suggested_action so the frontend drawer fires.
    if not result.get("success", False):
        raise HTTPException(status_code=422, detail=result)

    try:
        after_skills = load_skills(user_id=scope.user_id, team_id=scope.team_id)
        after_overrides = _load_enabled_overrides(scope.user_id)
        impact = _skill_cache_impact(
            source="skill_import",
            reason="skill_catalog_imported",
            previous_digest=before_digest,
            skills=after_skills,
            overrides=after_overrides,
            scope=scope,
            details={
                "github_url": req.github_url,
                "tier": req.tier,
                "imported": result.get("imported") or result.get("items") or [],
            },
        )
        runtime_event = cache_impact_runtime_event(impact)
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            conn.execute(
                """
                INSERT INTO agent.audit_events
                    (timestamp, action, user_id, success, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    datetime.now(UTC),
                    "SKILL_IMPORT_COMPLETED",
                    scope.user_id,
                    True,
                    json.dumps(
                        {
                            "github_url": req.github_url,
                            "tier": req.tier,
                            "updated_by": scope.actor,
                            "team_id": scope.team_id,
                            "tenant_id": _tenant_id(scope),
                            "cache_impact": impact,
                            "runtime_events": [runtime_event],
                        }
                    ),
                ),
            )
        result["cache_impact"] = impact
        result["runtime_events"] = [runtime_event]
    except Exception:  # noqa: BLE001
        logger.exception("skill import cache-impact audit failed — continuing")

    return result
