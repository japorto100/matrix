"""Skill Trigger Quality — aggregate coverage_score from audit_events.

When finder ranks a skill top-k, the coverage-judge later scores the whole
retrieved SET. If a skill is repeatedly present in low-coverage sets, its
trigger-description is probably too broad — it fires on queries it does
not actually serve.

Signals produced:
  n_found      : how often this skill was ranked top-k for a user query
  n_with_score : how often a coverage_score was recorded for that event
                 (0 when coverage gate was disabled / refinement off)
  avg_coverage : mean of recorded coverage scores (1-5 scale)
  false_rate   : fraction of events with coverage_score <  false_threshold

Higher false_rate = broader / worse trigger description. Spec §6.7.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC

import psycopg

logger = logging.getLogger(__name__)


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


@dataclass
class TriggerStat:
    skill_id: str
    n_found: int
    n_with_score: int
    avg_coverage: float
    false_rate: float
    verdict: str

    def as_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "n_found": self.n_found,
            "n_with_score": self.n_with_score,
            "avg_coverage": round(self.avg_coverage, 2) if self.avg_coverage else 0.0,
            "false_rate": round(self.false_rate, 3),
            "verdict": self.verdict,
        }


def _verdict(stat: dict, *, false_threshold_rate: float, min_n: int) -> str:
    if stat["n_found"] < min_n:
        return "INSUFFICIENT_DATA"
    if stat["n_with_score"] == 0:
        return "NO_COVERAGE_SCORES"
    if stat["false_rate"] >= false_threshold_rate:
        return "BROAD_TRIGGER_review_description"
    if stat["avg_coverage"] < 3.0:
        return "LOW_AVG_COVERAGE_review"
    return "OK"


def compute_trigger_quality(
    *,
    days: int = 30,
    false_threshold: float = 2.5,
    false_threshold_rate: float = 0.4,
    min_n: int = 5,
) -> list[TriggerStat]:
    """Return per-skill trigger-quality stats.

    `days`                 look-back window from now() (0 = all time)
    `false_threshold`      coverage_score below this counts as false-trigger
    `false_threshold_rate` verdict BROAD when this fraction is exceeded
    `min_n`                require at least N found-events per skill
    """
    since_clause = ""
    params: list = []
    if days > 0:
        since = datetime.now(UTC) - timedelta(days=days)
        since_clause = "AND ae.timestamp >= %s"
        params.append(since)

    # We read skill_ids per skill_found, then LEFT JOIN the coverage_score
    # that was recorded for the same query in the subsequent skill_refined /
    # skill_used event (same thread_id + same skill mentioned in source_skills
    # or skill_ids). Practically the same session_id/thread_id pair has the
    # trio {found, refined?, used}; we aggregate over all events that mention
    # the skill and have a coverage_score in metadata.
    sql = f"""
    WITH expanded AS (
        SELECT
            ae.thread_id,
            ae.timestamp,
            skill_id,
            (ae.metadata::jsonb ->> 'coverage_score')::float AS coverage_score,
            ae.action
        FROM agent.audit_events ae,
             LATERAL jsonb_array_elements_text(
                 ae.metadata::jsonb -> 'skill_ids'
             ) skill_id
        WHERE ae.action IN ('skill_found','skill_refined','skill_used')
          AND jsonb_typeof(ae.metadata::jsonb -> 'skill_ids') = 'array'
          {since_clause}

        UNION ALL

        SELECT
            ae.thread_id,
            ae.timestamp,
            src_id,
            (ae.metadata::jsonb ->> 'coverage_score')::float AS coverage_score,
            ae.action
        FROM agent.audit_events ae,
             LATERAL jsonb_array_elements_text(
                 ae.metadata::jsonb -> 'source_skills'
             ) src_id
        WHERE ae.action IN ('skill_refined','skill_used')
          AND jsonb_typeof(ae.metadata::jsonb -> 'source_skills') = 'array'
          {since_clause}
    )
    SELECT
        skill_id,
        COUNT(*) FILTER (WHERE action='skill_found') AS n_found,
        COUNT(coverage_score)                         AS n_with_score,
        AVG(coverage_score)                           AS avg_cov,
        COUNT(*) FILTER (
            WHERE coverage_score IS NOT NULL
              AND coverage_score < %s
        )::float /
        NULLIF(COUNT(coverage_score), 0)              AS false_rate
    FROM expanded
    GROUP BY skill_id
    ORDER BY skill_id
    """
    params_full = list(params) + list(params) + [false_threshold]

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            rows = conn.execute(sql, params_full).fetchall()
    except Exception as e:  # noqa: BLE001
        logger.warning("compute_trigger_quality failed: %s", e)
        return []

    out: list[TriggerStat] = []
    for r in rows:
        skill_id, n_found, n_with_score, avg_cov, false_rate = r
        stat = {
            "n_found": int(n_found or 0),
            "n_with_score": int(n_with_score or 0),
            "avg_coverage": float(avg_cov or 0.0),
            "false_rate": float(false_rate or 0.0),
        }
        out.append(
            TriggerStat(
                skill_id=skill_id,
                n_found=stat["n_found"],
                n_with_score=stat["n_with_score"],
                avg_coverage=stat["avg_coverage"],
                false_rate=stat["false_rate"],
                verdict=_verdict(
                    stat,
                    false_threshold_rate=false_threshold_rate,
                    min_n=min_n,
                ),
            )
        )
    return out
