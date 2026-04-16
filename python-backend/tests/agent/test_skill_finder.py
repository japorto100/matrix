"""Tests for agent.skills.finder (BM25 + RRF, dense optional).

Run lokal: AGENT_SKILL_FINDER_DENSE=0 pytest tests/agent/test_skill_finder.py -q
(ohne Dense kein sentence-transformers-Download beim ersten Import in _dense_ranks.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.skills.finder import find_skills_for_query, tokenize
from agent.skills.loader import Skill, parse_skill_file


def test_tokenize_basic() -> None:
    assert "oil" in tokenize("Brent crude oil price")


def test_find_skills_bm25_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_SKILL_FINDER_DENSE", "0")
    d = tmp_path / "oil-markets"
    d.mkdir()
    raw = """---
name: oil-markets
description: Energy and crude oil market analysis
category: research
---
Body about OPEC.
"""
    (d / "SKILL.md").write_text(raw, encoding="utf-8")
    s = parse_skill_file(d / "SKILL.md", tier="global")
    assert s is not None
    skills = [s]
    out = find_skills_for_query(skills, "crude oil OPEC energy", top_k=1)
    assert len(out) == 1
    assert out[0].name == "oil-markets"


def test_empty_query_returns_all(tmp_path: Path) -> None:
    p = tmp_path / "SKILL.md"
    p.write_text("x", encoding="utf-8")
    s = Skill(
        name="a",
        description="d",
        category="c",
        content="x",
        path=p,
    )
    assert find_skills_for_query([s], "") == [s]
