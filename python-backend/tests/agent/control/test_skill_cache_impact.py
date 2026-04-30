from __future__ import annotations

from pathlib import Path

from agent.control.request_scope import RequestScope
from agent.control.skills import _skill_cache_impact, _skill_catalog_digest
from agent.skills.loader import Skill


def _skill(enabled: bool = True) -> Skill:
    return Skill(
        name="memory-curator",
        description="Curate memory",
        category="memory",
        content="Use memory carefully.",
        path=Path("SKILL.md"),
        tier="global",
        enabled=enabled,
        assets={"scripts": {"curate.py": "print('ok')"}},
    )


def test_skill_catalog_digest_changes_on_effective_toggle() -> None:
    skills = [_skill()]
    before = _skill_catalog_digest(skills)
    after = _skill_catalog_digest(skills, overrides={"global:memory-curator": False})

    assert len(before) == 64
    assert before != after


def test_skill_cache_impact_marks_toggle_rebind_required() -> None:
    skills = [_skill()]
    scope = RequestScope(user_id="alice", team_id="team-a", actor="alice")
    before = _skill_catalog_digest(skills)

    impact = _skill_cache_impact(
        source="skill_toggle",
        reason="skill_enabled_state_changed",
        previous_digest=before,
        skills=skills,
        overrides={"global:memory-curator": False},
        scope=scope,
    )

    assert impact["contract"] == "agent-cache-impact/v1"
    assert impact["action"] == "rebind_required"
    assert impact["changed"] is True
    assert impact["scope"]["tenant_id"] == "matrix-local"
