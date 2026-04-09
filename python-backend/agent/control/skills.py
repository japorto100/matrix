"""Control Surface — Skills Registry (Slice 5 backend).

Wraps agent/skills/loader.py — exposes 3-tier skills (global/team/personal)
via REST. Read-only in Phase 1 except enable/disable toggle.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.skills.loader import load_skills

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "skills"])


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
    user_id: str = "local",
) -> dict[str, Any]:
    """List all skills (or filter by tier)."""
    try:
        skills = load_skills(user_id=user_id, team_id=None)
    except Exception as e:  # noqa: BLE001
        logger.warning("load_skills failed: %s", e)
        skills = []

    items = [_skill_to_dict(s, i) for i, s in enumerate(skills)]
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
            d["body"] = s.content  # full body, not just preview
            return d
    raise HTTPException(status_code=404, detail="Skill not found")


class PatchSkillRequest(BaseModel):
    enabled: bool


@router.patch("/skills/{skill_id}")
async def patch_skill(skill_id: str, req: PatchSkillRequest) -> dict[str, Any]:
    """Enable/disable a skill (bounded-write).

    Phase 1 limitation: this endpoint is currently a stub because the skills
    loader uses filesystem scanning — enable state is not persisted to DB yet.
    Phase 2: add a skills_enabled table or use a flat JSON file.
    """
    return {
        "status": "pending_phase2",
        "skill_id": skill_id,
        "target_enabled": req.enabled,
        "note": "Skill enable/disable not yet persisted — needs agent/skills/state.py (Phase 2)",
    }
