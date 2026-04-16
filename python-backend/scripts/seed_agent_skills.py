"""Seed global skills from filesystem into `agent.agent_skills`.

Usage:
  uv run python scripts/seed_agent_skills.py
"""

from __future__ import annotations

from agent.skills.loader import load_skills
from agent.skills.store_db import upsert_global_skill


def main() -> None:
    skills = load_skills()
    globals_only = [s for s in skills if s.tier == "global"]
    for skill in globals_only:
        upsert_global_skill(skill)
        print(f"seeded: {skill.name}")
    print(f"done: {len(globals_only)} global skills")


if __name__ == "__main__":
    main()
