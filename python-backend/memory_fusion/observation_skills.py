"""Observation -> Skill bridge for memory_fusion.

Kopie aus `agent/memory/observation_skills.py`, nur auf `memory_fusion`
umgebogen.
"""

from __future__ import annotations

import logging

from agent.llm_helper import extract_json, llm_call
from agent.skills.loader import SKILLS_BASE

logger = logging.getLogger(__name__)

OBSERVATION_TO_SKILL_PROMPT = """Analyze this consolidated observation from the memory system.
If it represents a recurring pattern, preference, or lesson that would help the agent
perform better in the future, convert it to a skill.

## Observation
{observation}

## Rules
- Only create a skill if the observation represents a RECURRING pattern (not a one-time event)
- The skill should be actionable (instructions the agent can follow)
- Return null if this observation is not skill-worthy

## Output (JSON)
{{
    "worthy": true/false,
    "name": "skill-name-kebab-case",
    "description": "one-line description",
    "category": "trading|risk|research|general",
    "content": "## Workflow\\n...\\n## Best Practices\\n..."
}}"""


async def observations_to_skills(user_id: str, max_observations: int = 20) -> list[str]:
    from memory_fusion.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return []

    try:
        from hindsight_api.models import RequestContext

        bank_id = get_bank_id(user_id)
        observations = await engine.list_mental_models_consolidated(
            bank_id=bank_id,
            limit=max_observations,
            request_context=RequestContext(),
        )

        if not observations:
            return []

        generated = []
        for obs in observations:
            text = obs.get("text", "")
            if not text or len(text) < 20:
                continue

            try:
                response = await llm_call(
                    OBSERVATION_TO_SKILL_PROMPT.format(observation=text),
                    max_tokens=1024,
                )
                data = extract_json(response)
                if not data.get("worthy"):
                    continue

                name = f"auto-obs-{data['name']}"
                skill_dir = SKILLS_BASE / "personal" / user_id / name
                skill_dir.mkdir(parents=True, exist_ok=True)

                from datetime import datetime

                skill_md = (
                    f"---\n"
                    f"name: {name}\n"
                    f"description: {data['description']}\n"
                    f"category: {data.get('category', 'general')}\n"
                    f"source: memory_fusion_observation\n"
                    f"generated: {datetime.now().isoformat()}\n"
                    f"user_id: {user_id}\n"
                    f"---\n\n"
                    f"{data['content']}\n"
                )
                (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
                generated.append(name)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skill generation from memory_fusion observation failed: %s", exc)
                continue
        return generated
    except Exception as exc:  # noqa: BLE001
        logger.warning("memory_fusion observations_to_skills failed: %s", exc)
        return []


async def memory_enriched_skill_retrieval(
    user_id: str,
    task_description: str,
    max_memories: int = 5,
) -> str:
    from memory_fusion.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return task_description

    try:
        from hindsight_api.engine.memory_engine import Budget
        from hindsight_api.models import RequestContext

        bank_id = get_bank_id(user_id)
        result = await engine.recall_async(
            bank_id=bank_id,
            query=task_description[:300],
            fact_type=["experience", "observation"],
            budget=Budget.LOW,
            max_tokens=500,
            request_context=RequestContext(),
        )
        if not result.results:
            return task_description
        memory_context = " | ".join(f.text for f in result.results[:max_memories])
        return f"{task_description} [Memory context: {memory_context}]"
    except Exception:
        return task_description


async def get_user_profile_tags(user_id: str) -> list[str]:
    from memory_fusion.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return []

    try:
        from hindsight_api.engine.memory_engine import Budget
        from hindsight_api.models import RequestContext

        bank_id = get_bank_id(user_id)
        result = await engine.recall_async(
            bank_id=bank_id,
            query="user preferences trading style risk tolerance",
            fact_type=["opinion"],
            budget=Budget.LOW,
            max_tokens=500,
            request_context=RequestContext(),
        )

        if not result.results:
            return []

        opinions_text = "\n".join(f"- {f.text}" for f in result.results[:5])
        response = await llm_call(
            f"Extract user profile tags from these opinions:\n{opinions_text}\n\n"
            f'Output JSON: {{"tags": ["tag1", "tag2"]}}',
            max_tokens=128,
        )
        data = extract_json(response)
        return data.get("tags", [])
    except Exception:
        return []
