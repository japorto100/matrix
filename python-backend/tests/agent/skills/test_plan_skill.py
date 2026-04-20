"""Tests for the domain-agnostic plan skill (agent/skills/global/plan/SKILL.md)."""
from __future__ import annotations

from agent.skills.loader import load_skills


def test_plan_skill_is_loaded():
    skills = load_skills()
    plan = next((s for s in skills if s.name == "plan"), None)
    assert plan is not None, "plan skill not discovered by loader"
    assert plan.category == "meta"


def test_plan_skill_description_covers_multiple_domains():
    """Description should trigger on non-coding cues so matrix's multi-domain
    use-cases (trading, research, ops) actually pick up the skill."""
    skills = load_skills()
    plan = next(s for s in skills if s.name == "plan")
    desc = plan.description.lower()

    # Coding-specific triggers
    assert "plan" in desc

    # Matrix-specific (non-coding) triggers — critical for the domain-
    # agnostic claim.
    assert "trading" in desc
    assert "research" in desc
    assert "migration" in desc or "operational" in desc

    # Deutsch + English cues
    assert "entwurf" in desc or "vorschlag" in desc
    assert "draft" in desc or "proposal" in desc or "outline" in desc


def test_plan_skill_body_enforces_read_only_in_plan_mode():
    """Core safety property — planning must not execute irreversible actions."""
    skills = load_skills()
    plan = next(s for s in skills if s.name == "plan")
    body = plan.content.lower()
    # The skill must explicitly prohibit destructive/irreversible action.
    assert "irreversible" in body or "do not execute" in body
    # Read-only gathering should be OK (we want grounded plans, not
    # hallucinated ones).
    assert "read-only" in body or "read only" in body


def test_plan_skill_has_required_structure_sections():
    skills = load_skills()
    plan = next(s for s in skills if s.name == "plan")
    body = plan.content

    # The skill prescribes a 7-section plan shape. Verify the required
    # headers are present in the skill-template so future edits don't
    # silently drop sections.
    for section in (
        "Ziel", "Goal",
        "Annahmen", "Assumptions",
        "Ansatz", "Approach",
        "Schritte", "Steps",
        "Risiken", "Risks",
    ):
        assert section in body, f"required plan section missing: {section}"
