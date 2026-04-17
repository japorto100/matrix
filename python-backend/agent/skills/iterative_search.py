"""Agentic Iterative Skill Retrieval (Paper 2604.04323 §3.2).

The paper's strongest retrieval method is "agentic hybrid w/ content":
Recall@5 = 65.5% vs 47.0% for direct semantic search. The mechanism that
produces that gain is *iterative query reformulation* — the agent looks at
initial candidates, judges whether they cover the task, and either accepts
or reformulates the query and searches again.

Our baseline `find_skills_for_query` is already "hybrid w/ content" (BM25 +
dense over name+description+body-preview). What's missing is the iterative
loop. This module adds it.

Budget: `AGENT_SKILL_ITERATIVE_MAX_ROUNDS` (default 2 — one initial + at
most one reformulation). Each round costs one LLM judge call. If the judge
is satisfied after round 0, we save the LLM call.

Enable: `AGENT_SKILL_ITERATIVE_SEARCH=1`. Default off because it costs 1-2
LLM calls per query.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.skills.loader import Skill

logger = logging.getLogger(__name__)


JUDGE_SYSTEM = """You evaluate a retrieved skill set for a user task.

Return JSON only, no prose:
{
  "satisfied": true|false,
  "reformulation": "<null or a better search query>",
  "reasoning": "<1 short sentence>"
}

Rules:
- `satisfied: true` means the retrieved skills collectively enable the task.
  Set this true when the top result clearly covers the core of the task.
- `satisfied: false` + a `reformulation` when obvious terms from the task are
  missing in the retrieved skills OR the retrieved skills are off-topic.
- Reformulations should be concise retrieval queries, not questions — e.g.
  "position sizing stop loss risk" instead of "How do I size my position?".
- If you cannot improve the query, return satisfied:true and reformulation:null
  rather than looping pointlessly.
"""


@dataclass
class IterativeSearchResult:
    picked: list[Skill]
    rounds: int
    queries: list[str]
    satisfied: bool


def _enabled() -> bool:
    v = os.environ.get("AGENT_SKILL_ITERATIVE_SEARCH", "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def _max_rounds() -> int:
    try:
        return max(1, int(os.environ.get("AGENT_SKILL_ITERATIVE_MAX_ROUNDS", "2")))
    except ValueError:
        return 2


async def _judge(
    *,
    query: str,
    candidates: list[Skill],
    history: list[str],
    api_key: str | None,
) -> tuple[bool, str | None]:
    """Return (satisfied, reformulation)."""
    from agent.llm_helper import llm_call

    desc = "\n".join(f"- {s.name}: {s.description}" for s in candidates) or "(none)"
    prompt = (
        f"Original user task:\n{query.strip()}\n\n"
        f"Retrieved candidates (round {len(history)}):\n{desc}\n\n"
        f"Previous queries tried: {json.dumps(history)}\n\n"
        "Is this set sufficient?"
    )
    try:
        raw = await llm_call(
            prompt,
            max_tokens=200,
            system=JUDGE_SYSTEM,
            api_key=api_key,
        )
    except Exception as e:  # noqa: BLE001
        logger.debug("iterative judge failed, fail-open satisfied: %s", e)
        return True, None

    text = (raw or "").strip()
    if "```" in text:
        # strip code fences if model emits them anyway
        parts = text.split("```")
        for p in parts:
            if "{" in p and "}" in p:
                text = p.removeprefix("json").strip()
                break
    try:
        data = json.loads(text[text.find("{") : text.rfind("}") + 1])
    except Exception:  # noqa: BLE001
        logger.debug("iterative judge non-JSON, fail-open: %r", text[:120])
        return True, None

    satisfied = bool(data.get("satisfied", True))
    reformulation = data.get("reformulation")
    if reformulation and not isinstance(reformulation, str):
        reformulation = None
    if reformulation:
        reformulation = reformulation.strip() or None
    return satisfied, reformulation


async def iterative_find(
    skills: list[Skill],
    query: str,
    *,
    top_k: int | None = None,
    api_key: str | None = None,
) -> IterativeSearchResult:
    """Run initial retrieval; optionally reformulate and re-retrieve.

    Always returns a result, even if the loop is disabled (then it's one
    round with the original query — identical to `find_skills_for_query`).
    """
    from agent.skills.finder import find_skills_for_query

    q = (query or "").strip()
    queries: list[str] = [q]
    picked = find_skills_for_query(skills, q, top_k=top_k)

    if not _enabled() or not skills:
        return IterativeSearchResult(picked, rounds=1, queries=queries, satisfied=True)

    rounds = _max_rounds()
    satisfied = True
    for _ in range(1, rounds):
        satisfied, reformulation = await _judge(
            query=q,
            candidates=picked,
            history=queries,
            api_key=api_key,
        )
        if satisfied or not reformulation or reformulation in queries:
            break
        queries.append(reformulation)
        next_picked = find_skills_for_query(skills, reformulation, top_k=top_k)
        # Merge de-dup — prefer earlier (higher-ranked) for the same skill id.
        seen: set[str] = set()
        merged: list[Skill] = []
        for s in picked + next_picked:
            key = f"{s.tier}:{s.name}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(s)
        picked = merged[: (top_k or len(merged))]

    return IterativeSearchResult(
        picked=picked, rounds=len(queries), queries=queries, satisfied=satisfied
    )
