"""Harness Evaluator — run agent variants against a search set (exec-17 Phase 6).

Meta-Harness paper: "The proposer never sees test-set results; its only feedback
comes from the search set." This module runs the agent with a given harness config
against representative queries and collects scores.

Usage:
  from agent.harness.evaluator import evaluate_search_set
  results = await evaluate_search_set(config_override={...})
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SEARCH_SET_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "harness"
    / "search_set"
    / "queries.json"
)


def load_search_set() -> list[dict[str, Any]]:
    """Load search-set queries from JSON file."""
    if not SEARCH_SET_PATH.exists():
        logger.warning("Search set not found: %s", SEARCH_SET_PATH)
        return []
    data = json.loads(SEARCH_SET_PATH.read_text(encoding="utf-8"))
    return data.get("queries", [])


async def evaluate_single(
    query: dict[str, Any],
    *,
    system_prompt_override: str = "",
) -> dict[str, Any]:
    """Run the agent on a single query and return audit-based scores.

    Uses a unique thread_id per evaluation to isolate traces.
    """
    from agent.harness.scorer import score_session

    eval_thread_id = f"eval-{uuid.uuid4().hex[:12]}"

    # Build a minimal agent execution
    try:
        from agent.context import AgentExecutionContext
        from agent.graph.runner import run_agent_loop

        ctx = AgentExecutionContext(
            user_id="harness-evaluator",
            thread_id=eval_thread_id,
            model="",  # Uses default from config
            system_prompt=system_prompt_override or "",
            tools=(),
        )

        messages = [{"role": "user", "content": query["message"]}]

        # Consume the SSE stream (we only care about audit side-effects)
        async for _ in run_agent_loop(ctx, messages):
            pass

    except Exception as e:
        logger.warning("Evaluation failed for %s: %s", query.get("id", "?"), e)
        return {
            "query_id": query.get("id", ""),
            "thread_id": eval_thread_id,
            "error": str(e),
        }

    # Score the session
    scores = await score_session(eval_thread_id)
    scores["query_id"] = query.get("id", "")
    scores["category"] = query.get("category", "")

    return scores


async def evaluate_search_set(
    *,
    system_prompt_override: str = "",
    max_queries: int = 0,
) -> dict[str, Any]:
    """Run the agent against the full search set and aggregate scores.

    Returns per-query scores + aggregated summary.
    """
    queries = load_search_set()
    if not queries:
        return {"error": "No search set queries found", "path": str(SEARCH_SET_PATH)}

    if max_queries > 0:
        queries = queries[:max_queries]

    results = []
    for query in queries:
        result = await evaluate_single(
            query, system_prompt_override=system_prompt_override
        )
        results.append(result)

    # Aggregate
    completed = sum(1 for r in results if r.get("completed", False))
    total_tokens = sum(r.get("total_tokens", 0) for r in results)
    avg_turns = sum(r.get("turns", 0) for r in results) / len(results) if results else 0
    tool_success_rates = [
        r.get("tool_success_rate", 0) for r in results if "tool_success_rate" in r
    ]
    avg_tool_success = (
        sum(tool_success_rates) / len(tool_success_rates) if tool_success_rates else 0
    )
    total_cost = sum(r.get("cost_estimate_usd", 0) for r in results)

    return {
        "queries_evaluated": len(results),
        "completion_rate": round(completed / max(len(results), 1), 3),
        "avg_turns": round(avg_turns, 2),
        "total_tokens": total_tokens,
        "avg_tool_success_rate": round(avg_tool_success, 3),
        "total_cost_usd": round(total_cost, 6),
        "per_query": results,
    }
