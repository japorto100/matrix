"""Pareto Frontier — multi-objective ranking for harness candidates (exec-17 Phase 6).

Meta-Harness paper: "maintains a Pareto frontier over evaluated harnesses."

A candidate is Pareto-optimal if no other candidate is better in ALL dimensions
simultaneously. The frontier is the set of all Pareto-optimal candidates.

Scoring dimensions (higher = better for all, after normalization):
  - completion_rate: % of queries completed
  - turn_efficiency: 1/turns (fewer turns = better)
  - tool_success_rate: % of tools that succeeded
  - token_efficiency: 1/tokens_per_query (fewer tokens = better)

Usage:
  candidates = load_all_candidates()
  frontier = compute_pareto_frontier(candidates)
  # frontier contains only non-dominated candidates
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CANDIDATES_DIR = Path(__file__).resolve().parents[3] / "data" / "harness" / "candidates"

# Dimensions to compare (all higher = better after normalization)
PARETO_DIMENSIONS = [
    "completion_rate",
    "turn_efficiency",
    "tool_success_rate",
    "token_efficiency",
]


def _dominates(a: dict[str, float], b: dict[str, float]) -> bool:
    """Returns True if candidate `a` dominates `b` (better or equal in all dims, strictly better in at least one)."""
    dominated_in_all = True
    strictly_better_in_one = False

    for dim in PARETO_DIMENSIONS:
        val_a = a.get(dim, 0.0)
        val_b = b.get(dim, 0.0)
        if val_a < val_b:
            dominated_in_all = False
            break
        if val_a > val_b:
            strictly_better_in_one = True

    return dominated_in_all and strictly_better_in_one


def compute_pareto_frontier(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute the Pareto frontier from a list of scored candidates.

    Each candidate must have the PARETO_DIMENSIONS keys.
    Returns only non-dominated candidates, sorted by completion_rate desc.
    """
    if not candidates:
        return []

    frontier = []
    for i, candidate in enumerate(candidates):
        dominated = False
        for j, other in enumerate(candidates):
            if i != j and _dominates(other, candidate):
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)

    frontier.sort(key=lambda c: c.get("completion_rate", 0), reverse=True)
    return frontier


def load_all_candidates() -> list[dict[str, Any]]:
    """Load all scored candidates from data/harness/candidates/."""
    if not CANDIDATES_DIR.exists():
        return []

    candidates = []
    for version_dir in sorted(CANDIDATES_DIR.glob("v*")):
        scores_path = version_dir / "scores.json"
        config_path = version_dir / "config.json"

        if not scores_path.exists():
            continue

        scores = json.loads(scores_path.read_text(encoding="utf-8"))
        scores["version"] = version_dir.name

        # Normalize to "higher = better" for Pareto comparison
        turns = scores.get("avg_turns", 10)
        tokens = scores.get("total_tokens", 100000)
        scores["turn_efficiency"] = round(1.0 / max(turns, 1), 3)
        scores["token_efficiency"] = round(1000.0 / max(tokens, 1), 6)

        if config_path.exists():
            scores["has_config"] = True

        candidates.append(scores)

    return candidates


def get_frontier_summary() -> dict[str, Any]:
    """Get a summary of the current Pareto frontier."""
    candidates = load_all_candidates()
    frontier = compute_pareto_frontier(candidates)

    return {
        "total_candidates": len(candidates),
        "frontier_size": len(frontier),
        "frontier": [
            {
                "version": c.get("version", ""),
                "completion_rate": c.get("completion_rate", 0),
                "avg_turns": c.get("avg_turns", 0),
                "tool_success_rate": c.get("tool_success_rate", 0),
                "total_tokens": c.get("total_tokens", 0),
                "cost_usd": c.get("total_cost_usd", 0),
            }
            for c in frontier
        ],
        "dominated": [c.get("version", "") for c in candidates if c not in frontier],
    }
