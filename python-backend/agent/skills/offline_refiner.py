"""Offline query-agnostic skill refinement (Paper 2604.04323 §4.1).

Query-agnostic refinement improves a skill *without* knowledge of the target
task. Paper's approach: generate synthetic queries the skill might serve,
run agents with/without it, use feedback to iterate. That's expensive. We
implement a cheaper single-pass variant that covers the key mechanic:

  1. Generate N synthetic tasks the skill would plausibly help with.
  2. One LLM rewrite that uses those tasks as "target scenarios" to drive
     a clearer / more actionable version of the skill body.

Cost: 2 LLM calls per skill. Matches paper §4.1 description: "apply
query-agnostic refinement only to the retrieved skills for each task,
treating this as an approximation of what a fully improved collection
would provide."

Result is written as a NEW row in `agent.agent_skills` with:
  - generation = parent.generation + 1
  - parent_skill_id = parent.id
  - enabled = true  (parent is disabled in the same transaction, so loader
                     picks up the refined version cleanly)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from agent.llm_helper import extract_json, llm_call
from agent.skills.loader import Skill

logger = logging.getLogger(__name__)


TASK_GEN_SYSTEM = """You generate realistic user tasks for a given skill.

Given the skill description and body, output N short realistic tasks that
an agent with this skill might be asked to handle.

Return JSON only:
{"tasks": ["task 1", "task 2", ...]}

Rules:
- Tasks should be concrete, with named assets/contexts when relevant
  (e.g. "size a 2% risk stop for BTCUSD at 68k" not "help with stops").
- Diverse — cover different sub-use-cases of the skill.
- Plausible — tasks a real user might ask, not synthetic edge cases.
"""


REWRITE_SYSTEM = """You refine an agent skill to be clearer, more actionable,
and better structured WITHOUT changing its domain or introducing tools the
original skill did not mention.

Preserve: goals, constraints, any concrete formulas, thresholds, or named
procedures. Keep terminology stable.

Improve: section structure, remove filler, add a short "## Examples" block
grounded in the target tasks, sharpen ambiguous imperatives.

Do NOT invent APIs, tool names, or external dependencies absent from the
original. Return plain markdown only, no code fences, no commentary.
"""


@dataclass
class RefineResult:
    original: Skill
    refined_content: str
    synthetic_tasks: list[str]
    ok: bool
    error: str | None = None


def _num_tasks() -> int:
    try:
        return max(3, int(os.environ.get("AGENT_SKILL_OFFLINE_TASKS", "6")))
    except ValueError:
        return 6


async def _generate_tasks(skill: Skill, *, api_key: str | None) -> list[str]:
    n = _num_tasks()
    prompt = (
        f"Skill name: {skill.name}\n"
        f"Description: {skill.description}\n\n"
        f"Skill body:\n{skill.content[:3000]}\n\n"
        f"Generate exactly {n} target tasks."
    )
    raw = await llm_call(
        prompt,
        max_tokens=600,
        system=TASK_GEN_SYSTEM,
        api_key=api_key,
    )
    data = extract_json(raw or "{}")
    tasks = data.get("tasks") or []
    return [t.strip() for t in tasks if isinstance(t, str) and t.strip()][:n]


async def _rewrite(
    skill: Skill,
    tasks: list[str],
    *,
    api_key: str | None,
) -> str:
    task_block = "\n".join(f"- {t}" for t in tasks) or "(none)"
    prompt = (
        f"Target tasks this refined skill should serve:\n{task_block}\n\n"
        f"Current skill name: {skill.name}\n"
        f"Current description: {skill.description}\n\n"
        f"Current body:\n{skill.content}\n\n"
        f"Return the refined skill markdown."
    )
    raw = await llm_call(
        prompt,
        max_tokens=2400,
        system=REWRITE_SYSTEM,
        api_key=api_key,
    )
    return (raw or "").strip()


async def refine_offline(skill: Skill, *, api_key: str | None = None) -> RefineResult:
    try:
        tasks = await _generate_tasks(skill, api_key=api_key)
    except Exception as e:  # noqa: BLE001
        return RefineResult(
            original=skill,
            refined_content=skill.content,
            synthetic_tasks=[],
            ok=False,
            error=f"task_gen: {e}",
        )

    try:
        refined = await _rewrite(skill, tasks, api_key=api_key)
    except Exception as e:  # noqa: BLE001
        return RefineResult(
            original=skill,
            refined_content=skill.content,
            synthetic_tasks=tasks,
            ok=False,
            error=f"rewrite: {e}",
        )

    if not refined:
        return RefineResult(
            original=skill,
            refined_content=skill.content,
            synthetic_tasks=tasks,
            ok=False,
            error="empty_rewrite",
        )

    return RefineResult(
        original=skill,
        refined_content=refined,
        synthetic_tasks=tasks,
        ok=True,
    )


def persist_refined(result: RefineResult) -> str | None:
    """Write refined skill as a new generation in agent.agent_skills.

    Disables the parent row in the same transaction so the loader picks up
    the refined version from `fetch_enabled_skills` without duplicate-name
    collisions. Returns the new UUID or None on failure.
    """
    if not result.ok:
        return None
    from agent.skills.store_db import _db_url

    parent = result.original
    try:
        import psycopg

        with psycopg.connect(_db_url(), autocommit=True) as conn:
            row = conn.execute(
                """
                SELECT id, generation
                FROM agent.agent_skills
                WHERE name = %s AND tier = 'global' AND enabled = true
                ORDER BY generation DESC
                LIMIT 1
                """,
                (parent.name,),
            ).fetchone()
            if not row:
                logger.warning(
                    "persist_refined: no enabled global parent for %s", parent.name
                )
                return None
            parent_id, parent_gen = row
            new_gen = int(parent_gen or 0) + 1

            conn.execute(
                "UPDATE agent.agent_skills SET enabled=false, updated_at=now() WHERE id=%s",
                (parent_id,),
            )

            ins_row = conn.execute(
                """
                INSERT INTO agent.agent_skills
                  (name, description, category, content, tier, generation,
                   parent_skill_id, enabled, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'global', %s, %s, true, now(), now())
                RETURNING id
                """,
                (
                    parent.name,
                    parent.description,
                    parent.category,
                    result.refined_content,
                    new_gen,
                    parent_id,
                ),
            ).fetchone()
            if not ins_row:
                logger.warning("persist_refined: INSERT returned no id")
                return None
            new_id = ins_row[0]

            conn.execute(
                """
                INSERT INTO agent.audit_events
                    (timestamp, action, success, metadata)
                VALUES (now(), 'skill_refined', true, %s::jsonb)
                """,
                (
                    json.dumps({
                        "skill_id": f"global:{parent.name}",
                        "mode": "offline",
                        "parent_id": str(parent_id),
                        "new_id": str(new_id),
                        "parent_generation": int(parent_gen or 0),
                        "new_generation": new_gen,
                        "synthetic_tasks": result.synthetic_tasks,
                    }),
                ),
            )
            return str(new_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("persist_refined failed")
        return None
