"""Tests for agent.skills.finder (BM25 + RRF, dense optional).

Run lokal: AGENT_SKILL_FINDER_DENSE=0 pytest tests/agent/test_skill_finder.py -q
(ohne Dense kein sentence-transformers-Download beim ersten Import in _dense_ranks.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.skills.finder import find_skills_for_query, tokenize
from agent.skills.loader import Skill, format_skills_for_prompt_async, parse_skill_file


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


def test_small_corpus_skips_dense_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = 0

    def fail_if_dense(_skills, _query):
        nonlocal calls
        calls += 1
        raise AssertionError("dense ranking should not cold-load for tiny corpora")

    monkeypatch.delenv("AGENT_SKILL_FINDER_DENSE", raising=False)
    monkeypatch.delenv("AGENT_SKILL_FINDER_DENSE_FORCE", raising=False)
    monkeypatch.setattr("agent.skills.finder._dense_ranks", fail_if_dense)
    skills = [
        Skill(
            name="market-research",
            description="Market sentiment and equity research",
            category="research",
            content="AAPL sentiment catalyst analyst positioning",
            path=tmp_path / "market",
        ),
        Skill(
            name="plan",
            description="Break down work",
            category="meta",
            content="planning",
            path=tmp_path / "plan",
        ),
    ]

    out = find_skills_for_query(skills, "current market sentiment for AAPL", top_k=1)

    assert calls == 0
    assert out[0].name == "market-research"


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


def test_no_lexical_overlap_returns_no_skills(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENT_SKILL_FINDER_DENSE", "0")
    skills = [
        Skill(
            name="market-research",
            description="Equity market sentiment and macro research",
            category="research",
            content="earnings rates catalysts",
            path=tmp_path / "market",
        ),
        Skill(
            name="trading-analysis",
            description="Trade setup and chart analysis",
            category="trading",
            content="entry stop target",
            path=tmp_path / "trading",
        ),
    ]

    assert find_skills_for_query(skills, "runner parity smoke", top_k=2) == []


@pytest.mark.asyncio
async def test_general_skills_are_query_gated_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("AGENT_SKILL_FINDER_DENSE", "0")
    monkeypatch.delenv("AGENT_SKILL_ALWAYS_LOAD_GENERAL", raising=False)
    skills = [
        Skill(
            name="memory-usage",
            description="Use when the task depends on user preferences or prior decisions",
            category="general",
            content="memory_add memory_search remember previous conversation",
            path=tmp_path / "memory",
            skill_type="general",
        ),
        Skill(
            name="market-research",
            description="Market sentiment and equity research",
            category="research",
            content="AAPL sentiment catalyst analyst positioning",
            path=tmp_path / "market",
        ),
    ]

    prompt = await format_skills_for_prompt_async(
        skills=skills,
        query="runner parity smoke",
        user_id="anonymous",
    )

    assert "memory-usage" not in prompt
    assert "market-research" not in prompt


@pytest.mark.asyncio
async def test_general_skill_still_loads_when_query_matches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("AGENT_SKILL_FINDER_DENSE", "0")
    skills = [
        Skill(
            name="memory-usage",
            description="Use when the task depends on user preferences or prior decisions",
            category="general",
            content="memory_add memory_search remember previous conversation",
            path=tmp_path / "memory",
            skill_type="general",
        ),
    ]

    prompt = await format_skills_for_prompt_async(
        skills=skills,
        query="Use memory_search to recall my previous risk preference",
        user_id="anonymous",
    )

    assert "memory-usage" in prompt
