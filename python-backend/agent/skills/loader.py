"""Skill Loader — 3-Tier Skill System (exec-10 Phase 3 + MetaClaw Insights).

Tiers:
  1. Global: Von uns erstellt, fuer alle User (agent/skills/global/)
  2. Team: Team-shared Skills (agent/skills/team/{team_id}/)
  3. Personal: Auto-generiert pro User (agent/skills/personal/{user_id}/)

Loading-Reihenfolge: Global → Team → Personal
Personal ueberschreibt Team, Team ueberschreibt Global (bei gleichem Skill-Name).

Skill-Format: YAML Frontmatter + Markdown (deer-flow / MetaClaw Pattern)
Versioning: Generation-Index in Frontmatter (MetaClaw Paper Sec. 3.2)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

SKILLS_BASE = Path(__file__).parent


@dataclass
class Skill:
    """Geladener Skill aus SKILL.md."""

    name: str
    description: str
    category: str
    content: str
    path: Path = field(repr=False)
    tier: Literal["global", "team", "personal"] = "global"
    owner: str | None = None  # team_id oder user_id
    generation: int = 0  # MetaClaw: Skill Generation Index
    enabled: bool = True


def parse_skill_file(skill_file: Path, tier: str = "global", owner: str | None = None) -> Skill | None:
    """Parst eine SKILL.md Datei mit YAML Frontmatter."""
    try:
        raw = skill_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read skill file %s: %s", skill_file, e)
        return None

    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    if not fm_match:
        logger.warning("No YAML frontmatter in %s", skill_file)
        return None

    metadata: dict[str, str] = {}
    for line in fm_match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip()] = value.strip()

    name = metadata.get("name")
    if not name:
        logger.warning("Skill has no name in %s", skill_file)
        return None

    content = raw[fm_match.end():]

    return Skill(
        name=name,
        description=metadata.get("description", ""),
        category=metadata.get("category", "general"),
        content=content.strip(),
        path=skill_file,
        tier=tier,
        owner=owner,
        generation=int(metadata.get("generation", "0")),
    )


def _scan_tier(
    base_dir: Path,
    tier: Literal["global", "team", "personal"],
    owner: str | None = None,
    category: str | None = None,
) -> list[Skill]:
    """Scannt ein Tier-Verzeichnis nach SKILL.md Dateien."""
    skills: list[Skill] = []
    if not base_dir.exists():
        return skills

    for item in sorted(base_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("_") or item.name == "__pycache__":
            continue

        skill_file = item / "SKILL.md"
        if not skill_file.exists():
            continue

        skill = parse_skill_file(skill_file, tier=tier, owner=owner)
        if skill is None:
            continue
        if category and skill.category != category:
            continue

        skills.append(skill)

    return skills


def load_skills(
    user_id: str | None = None,
    team_id: str | None = None,
    category: str | None = None,
    skills_base: Path | None = None,
) -> list[Skill]:
    """Laedt Skills aus allen 3 Tiers und merged sie.

    Loading-Reihenfolge: Global → Team → Personal
    Bei gleichem Name: Personal > Team > Global (Override-Semantik)

    Args:
        user_id: User-ID fuer Personal-Skills (optional)
        team_id: Team-ID fuer Team-Skills (optional)
        category: Nur Skills dieser Kategorie (optional)
        skills_base: Base-Verzeichnis (default: agent/skills/)

    Returns:
        Merged Liste, sortiert nach Name.
    """
    base = skills_base or SKILLS_BASE
    merged: dict[str, Skill] = {}

    # Tier 1: Global
    for skill in _scan_tier(base / "global", tier="global", category=category):
        merged[skill.name] = skill

    # Tier 2: Team
    if team_id:
        for skill in _scan_tier(base / "team" / team_id, tier="team", owner=team_id, category=category):
            merged[skill.name] = skill

    # Tier 3: Personal
    if user_id:
        for skill in _scan_tier(base / "personal" / user_id, tier="personal", owner=user_id, category=category):
            merged[skill.name] = skill

    skills = sorted(merged.values(), key=lambda s: s.name)
    logger.info(
        "Loaded %d skills (global=%d, team=%d, personal=%d)",
        len(skills),
        sum(1 for s in skills if s.tier == "global"),
        sum(1 for s in skills if s.tier == "team"),
        sum(1 for s in skills if s.tier == "personal"),
    )
    return skills


def format_skills_for_prompt(skills: list[Skill]) -> str:
    """Formatiert Skills als Prompt-Abschnitt fuer LLM Injection."""
    if not skills:
        return ""

    sections = ["## Available Skills\n"]
    for skill in skills:
        tier_badge = f"[{skill.tier}]" if skill.tier != "global" else ""
        sections.append(f"### {skill.name} {tier_badge}\n{skill.description}\n\n{skill.content}\n")

    return "\n".join(sections)
