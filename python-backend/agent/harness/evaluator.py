"""Harness Evaluator — run agent variants against a search set (exec-17 Phase 6).

Meta-Harness paper: "The proposer never sees test-set results; its only feedback
comes from the search set." This module runs the agent with a given harness config
against representative queries and collects scores.

Usage:
  from agent.harness.evaluator import evaluate_search_set
  results = await evaluate_search_set(config_override={...})
"""

from __future__ import annotations

import asyncio
import hashlib
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
EVAL_CACHE_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "harness" / "eval_cache.json"
)
EVALUATOR_CACHE_VERSION = "search-set-v1"


class EvaluationCache:
    """Small JSON-backed cache for deterministic harness eval inputs."""

    def __init__(self, path: Path = EVAL_CACHE_PATH) -> None:
        self.path = path
        self._entries: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._entries is not None:
            return self._entries
        if not self.path.exists():
            self._entries = {}
            return self._entries
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._entries = data if isinstance(data, dict) else {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ignoring unreadable evaluator cache %s: %s", self.path, exc)
            self._entries = {}
        return self._entries

    @staticmethod
    def key_for(query: dict[str, Any], *, system_prompt_override: str = "") -> str:
        payload = {
            "version": EVALUATOR_CACHE_VERSION,
            "query": {
                "id": query.get("id", ""),
                "message": query.get("message", ""),
                "category": query.get("category", ""),
            },
            "system_prompt_override": system_prompt_override or "",
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._load().get(key)
        return dict(entry) if isinstance(entry, dict) else None

    def set(self, key: str, value: dict[str, Any]) -> None:
        entries = self._load()
        cached = dict(value)
        cached["cache_key"] = key
        cached["cached"] = True
        entries[key] = cached

    def flush(self) -> None:
        if self._entries is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._entries, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
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
    eval_id: str | None = None,
) -> dict[str, Any]:
    """Run the agent on a single query and return audit-based scores.

    Uses a unique thread_id per evaluation to isolate traces.

    ``eval_id`` (exec-harness §4g.4): forwards to
    :func:`agent.harness.scorer.score_session` so the A/B row's
    ``harness_eval_id`` is populated. Callers inside
    :func:`evaluate_search_set` share the run's eval_id.
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

    # Score the session. eval_id (when provided) flows into the
    # ab_experiments.harness_eval_id column via the scorer's backfill.
    scores = await score_session(eval_thread_id, eval_id=eval_id)
    scores["query_id"] = query.get("id", "")
    scores["category"] = query.get("category", "")
    if eval_id:
        scores["eval_id"] = eval_id

    return scores


async def evaluate_search_set(
    *,
    system_prompt_override: str = "",
    max_queries: int = 0,
    eval_id: str | None = None,
    concurrency: int = 4,
    use_cache: bool = True,
    cache: EvaluationCache | None = None,
) -> dict[str, Any]:
    """Run the agent against the full search set and aggregate scores.

    Returns per-query scores + aggregated summary.

    ``eval_id``: groups every per-query fitness row under one
    harness-run identifier in ``agent.ab_experiments.harness_eval_id``.
    Auto-generated when omitted so each run has a unique id — omit the
    param in one-off callers and rely on the auto-id for Pareto
    dashboards to distinguish runs. Pass explicitly only for reruns /
    comparison runs that need to share an id.
    """
    queries = load_search_set()
    if not queries:
        return {"error": "No search set queries found", "path": str(SEARCH_SET_PATH)}

    if max_queries > 0:
        queries = queries[:max_queries]

    if not eval_id:
        eval_id = f"run-{uuid.uuid4().hex[:12]}"

    cache = cache or EvaluationCache()
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _run(query: dict[str, Any]) -> dict[str, Any]:
        cache_key = EvaluationCache.key_for(
            query,
            system_prompt_override=system_prompt_override,
        )
        if use_cache:
            cached = cache.get(cache_key)
            if cached is not None:
                result = dict(cached)
                result["cache_hit"] = True
                if eval_id:
                    result["eval_id"] = eval_id
                return result

        async with semaphore:
            result = await evaluate_single(
                query,
                system_prompt_override=system_prompt_override,
                eval_id=eval_id,
            )
        result["cache_hit"] = False
        result["cache_key"] = cache_key
        if use_cache and "error" not in result:
            cache.set(cache_key, result)
        return result

    results = await asyncio.gather(*(_run(query) for query in queries))
    if use_cache:
        cache.flush()

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
        "eval_id": eval_id,
        "queries_evaluated": len(results),
        "concurrency": max(1, concurrency),
        "cache_enabled": use_cache,
        "cache_hits": sum(1 for r in results if r.get("cache_hit")),
        "completion_rate": round(completed / max(len(results), 1), 3),
        "avg_turns": round(avg_turns, 2),
        "total_tokens": total_tokens,
        "avg_tool_success_rate": round(avg_tool_success, 3),
        "total_cost_usd": round(total_cost, 6),
        "per_query": results,
    }
