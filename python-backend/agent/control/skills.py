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

from agent.control.request_scope import RequestScope, resolve_scope
from agent.skills.loader import load_skills

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "skills"])


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def _load_enabled_overrides(user_id: str = "local") -> dict[str, bool]:
    """Return {skill_id: enabled} overrides from DB."""
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            rows = conn.execute(
                "SELECT skill_id, enabled FROM agent.skills_state WHERE user_id = %s",
                (user_id,),
            ).fetchall()
    except Exception as e:  # noqa: BLE001
        logger.warning("load skill state failed: %s", e)
        return {}
    return {row[0]: bool(row[1]) for row in rows}


def _skill_to_dict(skill: Any, idx: int) -> dict[str, Any]:
    return {
        "id": f"{skill.tier}:{skill.name}",
        "name": skill.name,
        "description": skill.description,
        "tier": skill.tier,
        "category": skill.category,
        "generation": skill.generation,
        "enabled": skill.enabled,
        "owner": skill.owner,
        "path": str(skill.path),
        "body_preview": skill.content[:400] if skill.content else "",
        "source": "builtin" if skill.tier == "global" else ("github" if skill.tier == "team" else "local"),
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
            raise HTTPException(status_code=400, detail="tier must be global|team|personal")
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
            d = _skill_to_dict(s, 0)
            overrides = _load_enabled_overrides(user_id)
            if sid in overrides:
                d["enabled"] = overrides[sid]
            d["body"] = s.content  # full body, not just preview
            return d
    raise HTTPException(status_code=404, detail="Skill not found")


class PatchSkillRequest(BaseModel):
    enabled: bool


class ImportSkillRequest(BaseModel):
    github_url: str
    name: str | None = None
    description: str | None = None
    tier: str = "personal"


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

    now = datetime.now(UTC)
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
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
                            "tenant_id": scope.tenant_id,
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


@router.post("/skills/import")
async def import_skill_from_github(
    req: ImportSkillRequest,
    request: Request,
    scope: RequestScope = Depends(resolve_scope),
) -> dict[str, Any]:
    """Persist an import request for later worker-based onboarding."""
    if not req.github_url.startswith(("https://github.com/", "http://github.com/")):
        raise HTTPException(status_code=400, detail="github_url must be a GitHub URL")
    if req.tier not in {"team", "personal"}:
        raise HTTPException(status_code=400, detail="tier must be team|personal")

    skill_name = (req.name or req.github_url.rstrip("/").split("/")[-1] or "imported-skill").strip()
    skill_id = f"{req.tier}:{skill_name}"
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
                    "SKILL_IMPORT_REQUESTED",
                    scope.user_id,
                    True,
                    json.dumps(
                        {
                            "skill_id": skill_id,
                            "github_url": req.github_url,
                            "tier": req.tier,
                            "name": req.name,
                            "description": req.description,
                            "updated_by": scope.actor,
                            "team_id": scope.team_id,
                            "tenant_id": scope.tenant_id,
                        }
                    ),
                ),
            )
    except Exception as e:  # noqa: BLE001
        logger.exception("import skill failed")
        raise HTTPException(status_code=500, detail=f"import: {e}") from e

    return {
        "status": "queued",
        "skill_id": skill_id,
        "tier": req.tier,
        "github_url": req.github_url,
    }
