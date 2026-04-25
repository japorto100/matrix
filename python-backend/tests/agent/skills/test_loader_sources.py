from __future__ import annotations

from pathlib import Path

from agent.skills.finder import filter_disabled_skills
from agent.skills.loader import Skill, load_skills, parse_skill_file


def _write_skill(
    root: Path,
    rel: str,
    *,
    name: str,
    description: str = "desc",
    category: str = "general",
    skill_type: str = "task_specific",
    api_version: str = "v1",
) -> Path:
    skill_dir = root / rel
    skill_dir.mkdir(parents=True)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "tool.sh").write_text("echo ok\n", encoding="utf-8")
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        f"""---
name: {name}
description: {description}
category: {category}
generation: 2
skill_type: {skill_type}
api_version: {api_version}
---
Body for {name}.
""",
        encoding="utf-8",
    )
    return skill_file


def test_parse_skill_file_preserves_api_version_type_and_assets(tmp_path: Path):
    skill_file = _write_skill(
        tmp_path,
        "global/research",
        name="research",
        skill_type="general",
        api_version="v2",
    )

    skill = parse_skill_file(skill_file)

    assert skill is not None
    assert skill.generation == 2
    assert skill.skill_type == "general"
    assert skill.api_version == "v2"
    assert skill.assets == {"scripts": {"tool.sh": "echo ok\n"}}


def test_load_skills_filesystem_merges_global_team_personal_overrides(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setenv("AGENT_SKILLS_SOURCE", "filesystem")
    _write_skill(tmp_path, "global/market", name="market", description="global")
    _write_skill(tmp_path, "team/team-1/market", name="market", description="team")
    _write_skill(
        tmp_path,
        "personal/alice/market",
        name="market",
        description="personal",
    )
    _write_skill(tmp_path, "global/news", name="news", description="global-news")

    skills = load_skills(user_id="alice", team_id="team-1", skills_base=tmp_path)

    assert [s.name for s in skills] == ["market", "news"]
    market = next(s for s in skills if s.name == "market")
    assert market.tier == "personal"
    assert market.owner == "alice"
    assert market.description == "personal"


def test_load_skills_db_source_uses_enabled_global_rows(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AGENT_SKILLS_SOURCE", "db")

    db_skill = Skill(
        name="db-global",
        description="from db",
        category="general",
        content="db body",
        path=Path("db://agent_skills/db-global"),
        tier="global",
        db_id="00000000-0000-0000-0000-000000000001",
    )

    monkeypatch.setattr(
        "agent.skills.store_db.fetch_enabled_skills",
        lambda **_kwargs: [db_skill],
    )

    skills = load_skills(skills_base=tmp_path)

    assert skills == [db_skill]


def test_load_skills_hybrid_prefers_db_global_over_filesystem(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AGENT_SKILLS_SOURCE", "hybrid")
    _write_skill(tmp_path, "global/shared", name="shared", description="filesystem")

    db_skill = Skill(
        name="shared",
        description="database",
        category="general",
        content="db body",
        path=Path("db://agent_skills/shared"),
        tier="global",
        db_id="00000000-0000-0000-0000-000000000002",
    )
    monkeypatch.setattr(
        "agent.skills.store_db.fetch_enabled_skills",
        lambda **_kwargs: [db_skill],
    )

    skills = load_skills(skills_base=tmp_path)

    assert len(skills) == 1
    assert skills[0].description == "database"
    assert skills[0].db_id == db_skill.db_id


def test_filter_disabled_skills_removes_disabled_and_all_disabled(monkeypatch):
    skills = [
        Skill(name="a", description="", category="", content="", path=Path("a"), tier="global"),
        Skill(name="b", description="", category="", content="", path=Path("b"), tier="team"),
    ]

    monkeypatch.setattr(
        "agent.skills.db_state.load_skill_toggle_overrides",
        lambda user_id: {"global:a": False},
    )
    assert [s.name for s in filter_disabled_skills(skills, "alice")] == ["b"]

    monkeypatch.setattr(
        "agent.skills.db_state.load_skill_toggle_overrides",
        lambda user_id: {"global:a": False, "team:b": False},
    )
    assert filter_disabled_skills(skills, "alice") == []
