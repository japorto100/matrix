"""Harness Scorer — compute quality scores from audit data (exec-17).

Meta-Harness paper: scores are 6% of proposer reads, but critical for
knowing which harness variant is better.

Scoring dimensions:
  - turn_efficiency: Fewer turns = better (inverse of turn count)
  - tool_success_rate: % of tools that succeeded
  - token_efficiency: Tokens per successful completion
  - memory_utilization: Were memories recalled and useful?
  - completion_rate: Did sessions complete without error?
  - cost_estimate: Rough USD cost based on token counts

**Phase-C §4g — A/B experiment backfill:**
:func:`score_session` additionally UPDATEs
``agent.ab_experiments.harness_fitness_score`` for the row that matches
this thread. The fitness score is a composite scalar in [0, 1] built
from the dimensions above so SQL aggregation (``AVG(...) GROUP BY
variant``) is straightforward. This replaces the previous-plan's
hand-rolled ``suspected_retry`` heuristic — meta-harness provides the
real user-satisfaction signal (Contrarian-CRITICAL-3 resolution).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# P4: replaced hardcoded MODEL_COST_PER_MTOK with LiteLLM-backed
# estimate_usage_cost. Keep a conservative fallback rate for models
# LiteLLM doesn't know (harness eval scenarios with fake/local models).
DEFAULT_COST_PER_MTOK = 3.0


def _estimate_cost(model: str, total_tokens: int) -> float:
    """Rough USD cost estimate.

    Splits ``total_tokens`` 60/40 input/output (empirical avg across matrix
    eval workloads) since audit-events don't preserve the split. For exact
    costs use :class:`agent.billing.insights.InsightsEngine` over spans.
    """
    from agent.billing.usage_pricing import CanonicalUsage, estimate_usage_cost

    input_tokens = int(total_tokens * 0.6)
    output_tokens = total_tokens - input_tokens
    usage = CanonicalUsage(input_tokens=input_tokens, output_tokens=output_tokens)
    result = estimate_usage_cost(model, usage)
    if result.amount_usd is not None:
        return round(float(result.amount_usd), 6)
    return round(total_tokens * DEFAULT_COST_PER_MTOK / 1_000_000, 6)


async def score_session(
    thread_id: str,
    *,
    eval_id: str | None = None,
) -> dict[str, Any]:
    """Score a completed agent session from audit data.

    Returns a dict with scoring dimensions. Higher is generally better
    for rates, lower is better for counts/cost.

    ``eval_id`` (exec-harness §4g.4 wiring): when the scorer runs as
    part of a specific meta-harness evaluation (not an ad-hoc backfill),
    passing the eval's identifier lets the backfill UPDATE populate
    ``agent.ab_experiments.harness_eval_id`` so fitness rows can be
    grouped by eval-run in Pareto dashboards. ``None`` → scheduled
    backfill (River worker) or ad-hoc invocation; column stays NULL.
    """
    from agent.audit.store import get_audit_store

    store = get_audit_store()
    events = await store.query(thread_id=thread_id, limit=500)

    if not events:
        return {"thread_id": thread_id, "error": "no events found"}

    llm_responses = [e for e in events if e.get("action") == "llm_response"]
    tool_results = [e for e in events if e.get("action") == "tool_result"]
    memory_recalls = [e for e in events if e.get("action") == "memory_recall"]
    memory_retains = [e for e in events if e.get("action") == "memory_retain"]
    consent_decisions = [e for e in events if e.get("action") == "consent_decision"]

    turns = len(llm_responses)
    total_tokens = sum(
        (e.get("metadata") or {}).get("token_usage", 0) for e in llm_responses
    )
    total_duration_ms = sum(e.get("duration_ms", 0) for e in llm_responses)
    tool_successes = sum(1 for t in tool_results if t.get("success"))
    tool_failures = len(tool_results) - tool_successes
    denied = sum(
        1
        for c in consent_decisions
        if (c.get("metadata") or {}).get("decision") in ("hard_deny", "deny")
    )
    completed = any((e.get("metadata") or {}).get("done") for e in llm_responses)

    # Detect model from metadata
    model = ""
    for e in llm_responses:
        m = (e.get("metadata") or {}).get("model", "")
        if m:
            model = m
            break

    # Session-based outcome signal (exec-18, if agent.sessions row exists)
    session_status = None
    session_summary = None
    try:
        from agent.sessions import get_session

        session = get_session(thread_id)
        if session:
            session_status = session.get("status")
            session_summary = session.get("summary")
    except Exception:  # noqa: BLE001
        pass

    # Skill events for this thread
    skill_events = [e for e in events if (e.get("action") or "").startswith("skill_")]
    skills_loaded = set()
    for se in skill_events:
        meta = se.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:  # noqa: BLE001
                meta = {}
        for sid in (meta.get("skill_ids") or []):
            skills_loaded.add(sid)

    result: dict[str, Any] = {
        "thread_id": thread_id,
        "model": model,
        "completed": completed,
        "session_status": session_status,
        "session_summary": session_summary,
        "turns": turns,
        "turn_efficiency": round(1.0 / max(turns, 1), 3),
        "total_tokens": total_tokens,
        "token_efficiency": round(total_tokens / max(turns, 1)),
        "total_duration_ms": round(total_duration_ms, 1),
        "tool_calls": len(tool_results),
        "tool_success_rate": round(tool_successes / max(len(tool_results), 1), 3),
        "tool_failures": tool_failures,
        "tools_denied": denied,
        "memory_recalls": len(memory_recalls),
        "memory_retains": len(memory_retains),
        "memory_utilization": len(memory_recalls) > 0,
        "skills_loaded": sorted(skills_loaded),
        "skill_events": len(skill_events),
        "cost_estimate_usd": _estimate_cost(model, total_tokens),
    }
    result["fitness_score"] = composite_fitness(result)

    # Phase-C §4g: backfill A/B row so `SELECT variant, AVG(harness_fitness_score)
    # FROM agent.ab_experiments GROUP BY variant` becomes the decision query.
    # Fire-and-forget via asyncio so a scorer call never blocks on DB fsync.
    try:
        import asyncio

        asyncio.create_task(
            backfill_ab_experiment_fitness(
                thread_id=thread_id,
                fitness_score=result["fitness_score"],
                eval_id=eval_id,
            )
        )
    except Exception:  # noqa: BLE001 — scorer must never break its caller
        logger.debug("ab_experiments fitness backfill dispatch failed", exc_info=True)

    return result


def composite_fitness(score: dict[str, Any]) -> float:
    """Collapse the multi-dimensional score dict into a scalar in [0, 1].

    Higher = better. Weights are intentionally simple so the scalar has
    an obvious interpretation; the raw dimensions remain available in
    the score dict for anyone who wants Pareto-front analysis.

    Weights (sum to 1.0):
      * 0.30 — tool_success_rate    (tool calls that returned results)
      * 0.25 — completion            (did the session finish cleanly)
      * 0.20 — turn_efficiency       (fewer turns = better, 1/turns)
      * 0.15 — memory_utilization    (1.0 if any recall, else 0.0)
      * 0.10 — cost_inverse          (1 / (1 + cost_usd), cheap = better)

    NULL-safe: missing or malformed fields contribute 0 so the scalar
    degrades gracefully on pre-P4 sessions.
    """
    def _as_float(v: Any, default: float = 0.0) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    tsr = max(0.0, min(1.0, _as_float(score.get("tool_success_rate"))))
    if score.get("tool_calls") == 0:
        tsr = 1.0  # no tool calls = no failures possible; don't penalise

    completed = 1.0 if score.get("completed") else 0.0
    # session_status="completed" is a stronger positive than just completed flag
    if score.get("session_status") == "completed":
        completed = 1.0
    elif score.get("session_status") == "errored":
        completed = 0.0

    turn_eff = max(0.0, min(1.0, _as_float(score.get("turn_efficiency"))))
    mem_util = 1.0 if score.get("memory_utilization") else 0.0

    cost = _as_float(score.get("cost_estimate_usd"))
    cost_inv = 1.0 / (1.0 + max(0.0, cost))

    fitness = (
        0.30 * tsr
        + 0.25 * completed
        + 0.20 * turn_eff
        + 0.15 * mem_util
        + 0.10 * cost_inv
    )
    return round(max(0.0, min(1.0, fitness)), 4)


async def backfill_ab_experiment_fitness(
    *,
    thread_id: str,
    fitness_score: float,
    eval_id: str | None = None,
    session_id: str | None = None,
) -> bool:
    """UPDATE agent.ab_experiments.harness_fitness_score for the matching row.

    Matches on ``thread_id`` by default (scorer's natural key) since the
    dispatcher writes thread_id at INSERT time. ``session_id`` optional
    override for cases where multiple threads share a session.

    Returns True on success, False on any DB error. Fail-soft — scorer
    callers must not be blocked by backfill failures.
    """
    if not thread_id and not session_id:
        return False

    try:
        import psycopg

        dsn = os.environ.get(
            "HINDSIGHT_DB_URL",
            "postgresql://postgres@localhost:5433/hindsight_dev",
        )
        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            if session_id:
                await conn.execute(
                    """
                    UPDATE agent.ab_experiments
                    SET harness_fitness_score = %s,
                        harness_eval_id       = COALESCE(%s, harness_eval_id)
                    WHERE session_id = %s
                    """,
                    (float(fitness_score), eval_id, session_id),
                )
            else:
                # Match on thread_id — update every A/B row for this thread
                # (typically one, but multi-turn threads may have several).
                await conn.execute(
                    """
                    UPDATE agent.ab_experiments
                    SET harness_fitness_score = %s,
                        harness_eval_id       = COALESCE(%s, harness_eval_id)
                    WHERE thread_id = %s
                    """,
                    (float(fitness_score), eval_id, thread_id),
                )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("ab_experiments fitness UPDATE failed: %s", exc)
        return False


async def score_sessions(
    thread_ids: list[str],
    *,
    eval_id: str | None = None,
) -> list[dict[str, Any]]:
    """Score multiple sessions. Returns list sorted by thread_id.

    ``eval_id`` forwards to each :func:`score_session` call — see there.
    """
    results = []
    for tid in thread_ids:
        results.append(await score_session(tid, eval_id=eval_id))
    return results
