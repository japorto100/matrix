"""Skill Pareto Ranking (exec-skills Phase 3c — OPTIONAL).

Status note (2026-04-15): Pareto-over-skills is a pattern TRANSLATED from
Meta-Harness (arxiv 2603.28052, where Pareto is applied to agent *config*
candidates). **None of the skill/memory papers mandate it** — not Skills in
the Wild (2604.04323), not MetaClaw, not Memory for Autonomous Agents.
A simpler success_rate gate with a usage threshold covers 95% of what this
module does for Promotion/Eviction. Keep this as infrastructure but do not
over-index on it; the real paper-driven wins are agentic iterative retrieval,
query-specific composition, and coverage gating (implemented elsewhere).

Reads from existing tables (no new schema):
  - agent.agent_skills      : usage_count, success_count (lifetime counters)
  - agent.audit_events      : skill_* events for time-windowed metrics
  - agent.skills_state      : user disables (negative signal)

Four dimensions mirror exec-skills §3c:
  1. success_rate     = success_count / max(usage_count, 1)
  2. usage_rate       = usage_count   (normalized per-skill)
  3. token_efficiency = 1 / avg_duration_ms   (cheap proxy; exact token
                        accounting requires llm_response metadata we don't
                        have yet — flagged)
  4. refinement_stability = 1 - (refine_count / max(use_count, 1))
                        (high = rarely needs refinement, already task-ready)

Non-dominated skills form the Pareto frontier — candidates for promotion
to `tier='global'` (if currently promoted/team) or retention.
Dominated skills with active user disables are eviction candidates.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import psycopg

logger = logging.getLogger(__name__)


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


@dataclass
class SkillScore:
    skill_id: str  # tier:name
    db_id: str | None
    name: str
    tier: str
    usage_count: int
    success_count: int
    refine_count: int
    use_count: int
    disable_count: int
    avg_duration_ms: float
    success_rate: float
    refinement_stability: float
    token_efficiency: float
    on_frontier: bool = False
    dominated_by: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "db_id": self.db_id,
            "name": self.name,
            "tier": self.tier,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "refine_count": self.refine_count,
            "use_count": self.use_count,
            "disable_count": self.disable_count,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "success_rate": round(self.success_rate, 4),
            "refinement_stability": round(self.refinement_stability, 4),
            "token_efficiency": round(self.token_efficiency, 6),
            "on_frontier": self.on_frontier,
            "dominated_by": self.dominated_by,
        }


def _dominates(a: SkillScore, b: SkillScore) -> bool:
    """a strictly dominates b: a >= b on all dims, > on at least one."""
    dims_a = (
        a.success_rate,
        a.usage_count,
        a.token_efficiency,
        a.refinement_stability,
    )
    dims_b = (
        b.success_rate,
        b.usage_count,
        b.token_efficiency,
        b.refinement_stability,
    )
    ge = all(x >= y for x, y in zip(dims_a, dims_b, strict=True))
    gt = any(x > y for x, y in zip(dims_a, dims_b, strict=True))
    return ge and gt


def _mark_frontier(scores: list[SkillScore]) -> None:
    for s in scores:
        s.on_frontier = True
        s.dominated_by = []
    for a in scores:
        for b in scores:
            if a is b:
                continue
            if _dominates(a, b):
                b.on_frontier = False
                b.dominated_by.append(a.skill_id)


def compute_pareto(*, min_usage: int = 0) -> list[SkillScore]:
    """Compute current Pareto frontier across all enabled skills in DB.

    `min_usage`: require at least N usage events before scoring (avoid
    Pareto-pollution by brand-new skills with 0 data). Spec suggests 20+.
    """
    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            rows = conn.execute(
                """
                SELECT
                    s.id::text                                 AS db_id,
                    s.name                                     AS name,
                    s.tier                                     AS tier,
                    s.usage_count                              AS usage_count,
                    s.success_count                            AS success_count
                FROM agent.agent_skills s
                WHERE s.enabled = true
                """
            ).fetchall()
            refine_rows = conn.execute(
                """
                SELECT
                    elem #>> '{}'                              AS skill_id,
                    COUNT(*)                                   AS n
                FROM agent.audit_events ae,
                     LATERAL jsonb_array_elements(
                         COALESCE(ae.metadata::jsonb, '{}'::jsonb) ->
                             'source_skills'
                     ) elem
                WHERE ae.action = 'skill_refined'
                GROUP BY 1
                """
            ).fetchall()
            use_rows = conn.execute(
                """
                SELECT
                    elem #>> '{}'                              AS skill_id,
                    COUNT(*)                                   AS n,
                    AVG(COALESCE(ae.duration_ms, 0))           AS avg_ms
                FROM agent.audit_events ae,
                     LATERAL jsonb_array_elements(
                         COALESCE(ae.metadata::jsonb, '{}'::jsonb) ->
                             'skill_ids'
                     ) elem
                WHERE ae.action = 'skill_used'
                GROUP BY 1
                """
            ).fetchall()
            disable_rows = conn.execute(
                """
                SELECT skill_id, COUNT(*) AS n
                FROM agent.skills_state
                WHERE enabled = false
                GROUP BY 1
                """
            ).fetchall()
    except Exception as e:  # noqa: BLE001
        logger.warning("compute_pareto DB read failed: %s", e)
        return []

    refine_counts = {r[0]: int(r[1]) for r in refine_rows if r[0]}
    use_counts: dict[str, tuple[int, float]] = {
        r[0]: (int(r[1]), float(r[2] or 0.0)) for r in use_rows if r[0]
    }
    disable_counts = {r[0]: int(r[1]) for r in disable_rows if r[0]}

    scored: list[SkillScore] = []
    for row in rows:
        db_id, name, tier, usage_count, success_count = row
        skill_id = f"{tier}:{name}"
        refine_n = refine_counts.get(skill_id, 0)
        use_n, avg_ms = use_counts.get(skill_id, (0, 0.0))
        disable_n = disable_counts.get(skill_id, 0)

        success_rate = (
            success_count / usage_count if usage_count > 0 else 0.0
        )
        refinement_stability = (
            1.0 - (refine_n / use_n) if use_n > 0 else 1.0
        )
        token_efficiency = 1.0 / avg_ms if avg_ms > 0 else 0.0

        if usage_count < min_usage:
            continue

        scored.append(
            SkillScore(
                skill_id=skill_id,
                db_id=db_id,
                name=name,
                tier=tier,
                usage_count=usage_count,
                success_count=success_count,
                refine_count=refine_n,
                use_count=use_n,
                disable_count=disable_n,
                avg_duration_ms=avg_ms,
                success_rate=success_rate,
                refinement_stability=refinement_stability,
                token_efficiency=token_efficiency,
            )
        )

    _mark_frontier(scored)
    return scored


def eviction_candidates(scores: list[SkillScore]) -> list[SkillScore]:
    """Dominated skills with any user-disable signal → eviction-worthy."""
    return [s for s in scores if not s.on_frontier and s.disable_count > 0]


def promotion_candidates(
    scores: list[SkillScore],
    *,
    min_users_success: int = 3,
    min_usage: int = 20,
) -> list[SkillScore]:
    """Promoted-tier frontier skills ready to be globalized.

    Spec §3c gate: non-dominated + 20+ usage + 3+ distinct users with success
    + no active user-disable.
    We can enforce usage + no-disable here; distinct-user-success requires
    session linkage (exec-18 future work) so is stubbed as comment.
    """
    out = []
    for s in scores:
        if not s.on_frontier:
            continue
        if s.tier != "promoted":
            continue
        if s.usage_count < min_usage:
            continue
        if s.disable_count > 0:
            continue
        # TODO: distinct-user success gate once session_memories exists
        out.append(s)
    return out
