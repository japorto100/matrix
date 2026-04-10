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
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Rough cost per 1M tokens (input/output averaged) — update as pricing changes
MODEL_COST_PER_MTOK: dict[str, float] = {
    "claude-sonnet-4-6": 6.0,
    "claude-haiku-4-5": 1.0,
    "claude-opus-4-6": 30.0,
    "gpt-4o": 5.0,
    "gpt-4o-mini": 0.3,
}
DEFAULT_COST_PER_MTOK = 3.0


def _estimate_cost(model: str, total_tokens: int) -> float:
    """Rough USD cost estimate."""
    rate = DEFAULT_COST_PER_MTOK
    for prefix, cost in MODEL_COST_PER_MTOK.items():
        if prefix in model:
            rate = cost
            break
    return round(total_tokens * rate / 1_000_000, 6)


async def score_session(thread_id: str) -> dict[str, Any]:
    """Score a completed agent session from audit data.

    Returns a dict with scoring dimensions. Higher is generally better
    for rates, lower is better for counts/cost.
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

    return {
        "thread_id": thread_id,
        "model": model,
        "completed": completed,
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
        "cost_estimate_usd": _estimate_cost(model, total_tokens),
    }


async def score_sessions(thread_ids: list[str]) -> list[dict[str, Any]]:
    """Score multiple sessions. Returns list sorted by thread_id."""
    results = []
    for tid in thread_ids:
        results.append(await score_session(tid))
    return results
