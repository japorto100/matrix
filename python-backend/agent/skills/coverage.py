"""Skill Coverage Scoring — LLM-judge on an initial retrieved set.

Paper 2604.04323 §4.2: query-specific refinement only helps when the
initial retrieved set is sufficiently relevant (LLM coverage score >= 3.83
in the paper). Below ~3.49 refinement brings no gains and can regress
weaker models (Kimi: 33.5 -> 26.7 with refinement on low-coverage sets).

We score the initial set on a 1-5 scale and treat that as a gate:
  >= 3.5 -> refine
  <  3.5 -> skip refine, use original top-k

Defaults and threshold are env-tunable so evals can A/B them.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.skills.loader import Skill

logger = logging.getLogger(__name__)


COVERAGE_SYSTEM = """You are a skill relevance judge.

Given a user task and a set of skills retrieved for it, rate how well the
skill set collectively covers what the task requires.

Scoring rubric (1-5):
  1 — skills are unrelated; agent will not benefit
  2 — tangentially related; only 1 skill touches the task
  3 — one skill is clearly relevant, others are noise
  4 — most skills cover different useful aspects of the task
  5 — skills collectively cover the task cleanly with little overlap

Return exactly one integer 1-5 and nothing else.
"""


# Per-model defaults. Honest provenance:
#
# PAPER-DIRECT (2604.04323 §4.2 + Table 3):
#   - Coverage 3.49 → refinement marginal / ineffective
#   - Coverage 3.83 → refinement substantial gain
#   - Global baseline 3.5 hugs that boundary — that's the Paper-anchored
#     default used when no model is resolved.
#
# PER-MODEL VALUES BELOW ARE INTERPRETATIONS, NOT TABLE VALUES:
#   Paper reports qualitatively that Claude gains with refinement across
#   most settings, while Kimi REGRESSED on SKILLSBENCH w/ curated
#   (33.5 → 26.7) and Qwen regressed there too (31.6 → 26.2). Both of
#   those regressions occurred at Paper-measured coverage 4.01 — meaning
#   high coverage alone is NOT sufficient for Kimi/Qwen; they misjudge
#   which skills are useful during self-evaluation.
#
#   Conclusion: weaker models need a stricter gate than the 3.5 global
#   default. We ship the below as pragmatic starting points — override
#   per deployment via AGENT_SKILL_COVERAGE_THRESHOLD_<FAMILY> env vars
#   once we have local eval data.
_MODEL_THRESHOLD_DEFAULTS: dict[str, float] = {
    "claude": 3.0,   # tolerant; Paper: gains across coverage levels
    "qwen":   4.0,   # middle; Paper: regression on curated, gain on TB
    "kimi":   4.5,   # strict; Paper: strongest regression — needs high bar
}


def _coverage_threshold(model: str | None = None) -> float:
    """Resolve the coverage gate threshold.

    Priority:
      1. global override `AGENT_SKILL_COVERAGE_THRESHOLD`
      2. per-model override `AGENT_SKILL_COVERAGE_THRESHOLD_<KEY>` (KEY in
         uppercase, e.g. CLAUDE / KIMI / QWEN) if the current model name
         matches that key substring
      3. baked default for that model family (see _MODEL_THRESHOLD_DEFAULTS)
      4. 3.5 fallback
    """
    override = os.environ.get("AGENT_SKILL_COVERAGE_THRESHOLD", "").strip()
    if override:
        try:
            return float(override)
        except ValueError:
            pass

    if model is None:
        model = os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "")
    m = (model or "").lower()

    for key, default in _MODEL_THRESHOLD_DEFAULTS.items():
        if key in m:
            per_model = os.environ.get(
                f"AGENT_SKILL_COVERAGE_THRESHOLD_{key.upper()}", ""
            ).strip()
            if per_model:
                try:
                    return float(per_model)
                except ValueError:
                    pass
            return default
    return 3.5


def _coverage_enabled() -> bool:
    v = os.environ.get("AGENT_SKILL_COVERAGE_GATE", "1").strip().lower()
    return v in ("1", "true", "yes", "on")


async def score_coverage(
    skills: list["Skill"],
    query: str,
    *,
    api_key: str | None = None,
) -> float:
    """Return coverage score in [1.0, 5.0]. On failure returns 5.0 (fail-open)."""
    if not skills or not query.strip():
        return 5.0

    from agent.llm_helper import llm_call

    descriptors = "\n".join(
        f"- {s.name}: {s.description}" for s in skills
    )
    prompt = (
        f"User task:\n{query.strip()}\n\n"
        f"Retrieved skills:\n{descriptors}\n\n"
        f"Score (1-5 integer only):"
    )
    try:
        out = await llm_call(
            prompt,
            max_tokens=4,
            system=COVERAGE_SYSTEM,
            api_key=api_key,
        )
    except Exception as e:  # noqa: BLE001
        logger.debug("coverage score failed, fail-open: %s", e)
        return 5.0

    txt = (out or "").strip()
    for ch in txt:
        if ch.isdigit():
            try:
                n = int(ch)
                return float(min(max(n, 1), 5))
            except ValueError:
                continue
    return 5.0


async def should_refine(
    skills: list["Skill"],
    query: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
) -> tuple[bool, float]:
    """Return (refine?, score). Respects AGENT_SKILL_COVERAGE_GATE=0 bypass.

    `model` lets callers pass the active runtime model so the per-family
    threshold (Claude 3.0 / Qwen 4.0 / Kimi 4.5) applies. Omit to read from
    `AGENT_DEFAULT_UTILITY_MODEL` env.
    """
    if not _coverage_enabled():
        return True, -1.0
    score = await score_coverage(skills, query, api_key=api_key)
    return score >= _coverage_threshold(model), score
