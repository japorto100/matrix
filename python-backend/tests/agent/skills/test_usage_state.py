from __future__ import annotations

from pathlib import Path

from agent.control import skills as control_skills
from agent.skills.loader import Skill
from agent.skills.usage_state import record_prompt_usage, record_view, set_pinned


def _skill(tmp_path: Path) -> Skill:
    return Skill(
        name="plan",
        description="Break down work",
        category="meta",
        content="Steps",
        path=tmp_path / "plan" / "SKILL.md",
        tier="global",
    )


def test_usage_state_counts_prompt_usage_views_and_pin(tmp_path: Path) -> None:
    skill = _skill(tmp_path)

    record_prompt_usage([skill], skills_base=tmp_path)
    record_view("global:plan", skills_base=tmp_path)
    pinned = set_pinned("global:plan", True, skills_base=tmp_path)

    assert pinned["use_count"] == 1
    assert pinned["view_count"] == 1
    assert pinned["pinned"] is True


def test_control_skill_dict_exposes_lifecycle_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    usage_path = tmp_path / "usage.json"
    monkeypatch.setenv("AGENT_SKILL_USAGE_STATE_PATH", str(usage_path))
    skill = _skill(tmp_path)
    record_prompt_usage([skill], skills_base=tmp_path)
    set_pinned("global:plan", True, skills_base=tmp_path)

    payload = control_skills._skill_to_dict(skill, 0)

    assert payload["id"] == "global:plan"
    assert payload["usage"]["use_count"] == 1
    assert payload["pinned"] is True
    assert payload["lifecycle_state"] == "active"
