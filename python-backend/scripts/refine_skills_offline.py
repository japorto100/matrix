"""CLI: offline query-agnostic refinement for global skills.

Usage:
  AGENT_DEFAULT_UTILITY_MODEL=... HINDSIGHT_DB_URL=... \
      python scripts/refine_skills_offline.py [--name NAME] [--dry-run]

Writes each refined skill as generation+1 in `agent.agent_skills` and
disables the parent row. Skips a skill if the LLM rewrite fails.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agent.skills.loader import load_skills
from agent.skills.offline_refiner import persist_refined, refine_offline


async def run(only_name: str | None, dry_run: bool) -> int:
    skills = [s for s in load_skills() if s.tier == "global"]
    if only_name:
        skills = [s for s in skills if s.name == only_name]
    if not skills:
        print("no skills to refine")
        return 1

    exit_code = 0
    for skill in skills:
        print(f"\n== refining {skill.name} (gen {skill.generation}) ==")
        result = await refine_offline(skill)
        if not result.ok:
            print(f"  FAIL: {result.error}")
            exit_code = max(exit_code, 2)
            continue
        print(f"  tasks generated: {len(result.synthetic_tasks)}")
        for t in result.synthetic_tasks[:3]:
            print(f"    - {t}")
        print(
            f"  original={len(skill.content)}ch  refined={len(result.refined_content)}ch"
        )

        if dry_run:
            print("  (dry-run, skip persist)")
            continue
        new_id = persist_refined(result)
        if new_id:
            print(f"  persisted new generation → id={new_id}")
        else:
            print("  persist FAILED")
            exit_code = max(exit_code, 3)
    return exit_code


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--name", help="refine only the skill with this name")
    p.add_argument("--dry-run", action="store_true", help="do not write to DB")
    args = p.parse_args()
    sys.exit(asyncio.run(run(args.name, args.dry_run)))


if __name__ == "__main__":
    main()
