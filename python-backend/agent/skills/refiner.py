"""Query-specific skill refinement (exec-skills Phase 2 + Paper 2604.04323).

Two modes (env AGENT_SKILL_REFINE_MODE):
  - per_skill    : each skill refined independently (legacy, 1 LLM call per skill)
  - compose      : all retrieved skills merged into ONE synthesized block
                   (default; matches paper's §4.1 "merge and synthesize across
                   multiple retrieved skills")

Composition is the paper's main recommendation. Per-skill is kept as a
fallback because composition can mask noise from weaker retrievals.

Refined skills are ephemeral — they live only for the current turn in the
prompt, never persisted.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import replace
from pathlib import Path

from agent.llm_helper import llm_call
from agent.resilience.error_classifier import RecoveryStrategy, classify_error
from agent.skills.loader import Skill

logger = logging.getLogger(__name__)


# Recovery strategies worth a single retry for short, ephemeral refiner calls.
# Format-errors / auth / upstream_unavailable / billing go straight to fallback.
_REFINER_RETRY_STRATEGIES: frozenset[RecoveryStrategy] = frozenset({
    RecoveryStrategy.retry,
    RecoveryStrategy.backoff_then_retry,
    RecoveryStrategy.backoff_then_rotate,
})


def _should_retry_refiner(exc: BaseException) -> tuple[bool, str]:
    """Classify a refiner-LLM exception and decide one-shot retry.

    Returns ``(retry, reason_str)`` so the caller can log the classification
    without pulling in classify_error itself.
    """
    result = classify_error(exc)
    return (result.recovery in _REFINER_RETRY_STRATEGIES), result.reason.value


# Keep retry backoff tiny by default — refiner blocks the system-prompt build.
# Tests override via AGENT_SKILL_REFINE_RETRY_SLEEP=0.
_RETRY_SLEEP_ENV = "AGENT_SKILL_REFINE_RETRY_SLEEP"


def _retry_sleep_seconds() -> float:
    try:
        return max(0.0, float(os.environ.get(_RETRY_SLEEP_ENV, "0.5")))
    except (TypeError, ValueError):
        return 0.5


PER_SKILL_SYSTEM = """You refine a single agent skill for a user task.

Rules:
- Keep the skill shorter and more specific to the user query.
- Preserve critical steps, constraints and domain terminology.
- Remove irrelevant sections.
- Do not invent tools, APIs or capabilities not present in the original skill.
- Return plain markdown only, no code fences, no commentary.
"""


COMPOSE_SYSTEM = """You synthesize one coherent skill for a user task by merging
multiple retrieved skills.

Rules:
- Produce a single markdown block with sections: ## Goal, ## Workflow,
  ## Constraints, ## Output (omit any section that has nothing relevant).
- Merge overlapping steps; prefer the most specific formulation.
- Keep only content that is useful for THIS user query — drop unrelated parts.
- Do NOT invent tools, APIs or constraints absent from the source skills.
- If the sources contradict, pick the one more appropriate for the query and
  note the trade-off in one sentence inside ## Constraints.
- Return plain markdown only, no code fences, no commentary.
"""


def _mode() -> str:
    v = os.environ.get("AGENT_SKILL_REFINE_MODE", "compose").strip().lower()
    return v if v in ("per_skill", "compose") else "compose"


async def _refine_per_skill(
    skills: list[Skill],
    *,
    query: str,
    context_hint: str,
    api_key: str | None,
) -> list[Skill]:
    refined: list[Skill] = []
    for skill in skills:
        prompt = (
            f"User query:\n{query.strip()}\n\n"
            f"Context hint:\n{context_hint.strip() or '(none)'}\n\n"
            f"Skill name: {skill.name}\n"
            f"Skill description: {skill.description}\n\n"
            f"Original skill markdown:\n{skill.content}\n"
        )
        try:
            out = await llm_call(
                prompt,
                max_tokens=1200,
                system=PER_SKILL_SYSTEM,
                api_key=api_key,
            )
        except Exception as e:  # noqa: BLE001
            retry, reason = _should_retry_refiner(e)
            logger.warning(
                "per-skill refine failed for %s (reason=%s, retry=%s): %s",
                skill.name, reason, retry, e,
            )
            if retry:
                await asyncio.sleep(_retry_sleep_seconds())
                try:
                    out = await llm_call(
                        prompt,
                        max_tokens=1200,
                        system=PER_SKILL_SYSTEM,
                        api_key=api_key,
                    )
                except Exception as e2:  # noqa: BLE001
                    logger.warning(
                        "per-skill refine retry failed for %s: %s", skill.name, e2,
                    )
                    refined.append(skill)
                    continue
            else:
                refined.append(skill)
                continue
        content = (out or "").strip() or skill.content
        refined.append(replace(skill, content=content))
    return refined


async def _refine_compose(
    skills: list[Skill],
    *,
    query: str,
    context_hint: str,
    api_key: str | None,
) -> list[Skill]:
    """Merge N skills -> 1 synthesized skill."""
    blocks: list[str] = []
    for i, s in enumerate(skills, 1):
        blocks.append(
            f"### Source skill {i}: {s.name}\n"
            f"Description: {s.description}\n\n"
            f"{s.content}\n"
        )
    prompt = (
        f"User query:\n{query.strip()}\n\n"
        f"Context hint:\n{context_hint.strip() or '(none)'}\n\n"
        f"You are given {len(skills)} retrieved skill(s). "
        f"Synthesize them into one coherent skill tailored to the query.\n\n"
        + "\n\n".join(blocks)
    )

    try:
        out = await llm_call(
            prompt,
            max_tokens=2000,
            system=COMPOSE_SYSTEM,
            api_key=api_key,
        )
    except Exception as e:  # noqa: BLE001
        retry, reason = _should_retry_refiner(e)
        logger.warning("compose refine failed (reason=%s, retry=%s): %s", reason, retry, e)
        if not retry:
            return skills
        await asyncio.sleep(_retry_sleep_seconds())
        try:
            out = await llm_call(
                prompt,
                max_tokens=2000,
                system=COMPOSE_SYSTEM,
                api_key=api_key,
            )
        except Exception as e2:  # noqa: BLE001
            logger.warning("compose refine retry failed: %s", e2)
            return skills

    content = (out or "").strip()
    if not content:
        return skills

    source_names = ",".join(s.name for s in skills)
    composed = Skill(
        name=f"composed:{source_names[:80]}",
        description=f"Synthesized for: {query.strip()[:120]}",
        category=skills[0].category if skills else "general",
        content=content,
        path=Path(f"composed://{source_names}"),
        tier=skills[0].tier if skills else "global",
        owner=None,
        generation=0,
        enabled=True,
        db_id=None,
    )
    return [composed]


async def refine_skills_for_query(
    skills: list[Skill],
    *,
    query: str,
    context_hint: str = "",
    api_key: str | None = None,
) -> list[Skill]:
    """Return refined skills for this turn.

    In compose mode returns a single synthesized skill. In per_skill mode
    returns one refined copy per input. On total failure returns the
    originals unchanged.
    """
    if not skills or not query.strip():
        return skills

    mode = _mode()
    if mode == "per_skill":
        return await _refine_per_skill(
            skills, query=query, context_hint=context_hint, api_key=api_key
        )
    return await _refine_compose(
        skills, query=query, context_hint=context_hint, api_key=api_key
    )
