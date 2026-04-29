"""Pareto Frontier — multi-objective ranking for harness candidates (exec-17 Phase 6).

Meta-Harness paper: "maintains a Pareto frontier over evaluated harnesses."

A candidate is Pareto-optimal if no other candidate is better in ALL dimensions
simultaneously. The frontier is the set of all Pareto-optimal candidates.

Ranking dimensions (higher = better for all, after normalization):
  - trace_gate_pass_rate: deterministic acceptance gates passed
  - completion_rate: % of queries completed
  - fitness_score: scalar scorer output
  - tool_success_rate: % of tool results that succeeded
  - turn_efficiency: 1/turns (fewer turns = better)
  - token_efficiency: 1000/tokens_per_query (fewer tokens = better)
  - cost_efficiency: 1/(1+USD cost)
  - latency_efficiency: 1000/ms

Memory use is intentionally not a Pareto objective. Memory correctness belongs
in trace gates, because many scenarios should not use memory at all.

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

CANDIDATES_DIR = Path(__file__).resolve().parents[2] / "data" / "harness" / "candidates"
META_HARNESS_RUNS_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "meta_harness" / "runs"
)

# Dimensions to compare (all higher = better after normalization)
PARETO_DIMENSIONS = [
    "trace_gate_pass_rate",
    "completion_rate",
    "fitness_score",
    "tool_success_rate",
    "turn_efficiency",
    "token_efficiency",
    "cost_efficiency",
    "latency_efficiency",
]


def _feasibility_failures(candidate: dict[str, Any]) -> list[str]:
    """Hard gates before Pareto trade-offs: completed scenarios and trace gates."""
    failures: list[str] = []
    if _as_float(candidate.get("completion_rate")) < 1.0:
        failures.append("completion_rate < 1.0")
    if _as_float(candidate.get("trace_gate_pass_rate")) < 1.0:
        failures.append("trace_gate_pass_rate < 1.0")
    return failures


def _is_feasible(candidate: dict[str, Any]) -> bool:
    return not _feasibility_failures(candidate)


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

    normalized = [_normalize_candidate(candidate) for candidate in candidates]
    feasible = [candidate for candidate in normalized if candidate["feasible"]]
    ranking_pool = feasible or normalized

    frontier = []
    for i, candidate in enumerate(ranking_pool):
        dominated = False
        for j, other in enumerate(ranking_pool):
            if i != j and _dominates(other, candidate):
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)

    frontier.sort(key=_ranking_key, reverse=True)
    return frontier


def _ranking_key(candidate: dict[str, Any]) -> tuple:
    return (
        bool(candidate.get("feasible")),
        _as_float(candidate.get("trace_gate_pass_rate")),
        _as_float(candidate.get("completion_rate")),
        _as_float(candidate.get("fitness_score")),
        _as_float(candidate.get("tool_success_rate")),
        _as_float(candidate.get("cost_efficiency")),
        _as_float(candidate.get("token_efficiency")),
        str(candidate.get("version") or candidate.get("candidate_id") or ""),
    )


def _normalize_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with all Pareto dimensions present and normalized."""
    entry = dict(candidate)
    turns = _as_float(entry.get("avg_turns") or entry.get("turns"), 10.0)
    tokens = _as_float(
        entry.get("avg_tokens") or entry.get("total_tokens"),
        100000.0,
    )
    cost = _as_float(entry.get("total_cost_usd") or entry.get("cost_usd"), 0.0)
    duration_ms = _as_float(
        entry.get("avg_duration_ms") or entry.get("total_duration_ms"),
        0.0,
    )
    entry.setdefault("turn_efficiency", round(1.0 / max(turns, 1.0), 4))
    entry.setdefault("token_efficiency", round(1000.0 / max(tokens, 1.0), 6))
    entry.setdefault("cost_efficiency", round(1.0 / (1.0 + max(cost, 0.0)), 6))
    entry.setdefault(
        "latency_efficiency",
        round(1000.0 / max(duration_ms, 1.0), 6) if duration_ms > 0 else 1.0,
    )
    entry.setdefault("trace_gate_pass_rate", 0.0)
    entry.setdefault("completion_rate", 0.0)
    entry.setdefault("fitness_score", entry.get("avg_fitness_score", 0.0))
    entry.setdefault("tool_success_rate", 0.0)
    failures = _feasibility_failures(entry)
    entry["feasible"] = not failures
    entry["feasibility_failures"] = failures
    return entry


def load_all_candidates() -> list[dict[str, Any]]:
    """Load all scored candidates from DB + Meta-Harness/legacy filesystems.

    DB source: agent.component_configs WHERE component_id='harness.default'
    Meta-Harness source: data/meta_harness/runs/*/candidates/*/aggregate.json
    Legacy source: data/harness/candidates/v*/scores.json
    Both are merged, deduplicated by version label.
    """
    candidates: list[dict[str, Any]] = []
    seen_versions: set[str] = set()

    # ── Meta-Harness run artifacts (primary for Feature 016) ─────────
    candidates.extend(_load_meta_harness_candidates(seen_versions))

    # ── DB path (primary, exec-18) ───────────────────────────────────
    try:
        candidates.extend(_load_candidates_db(seen_versions))
    except Exception:  # noqa: BLE001
        pass

    # ── Filesystem path (legacy Meta-Harness pattern) ────────────────
    candidates.extend(_load_candidates_fs(seen_versions))

    return candidates


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.debug("failed to read %s: %s", path, exc)
        return None


def _fallback_meta_aggregate(candidate_dir: Path) -> dict[str, Any] | None:
    """Infer aggregate metrics from older Feature-016 artifacts."""
    results_path = candidate_dir / "results.json"
    results = _load_json(results_path)
    if not isinstance(results, list):
        single = _load_json(candidate_dir / "result.json")
        results = [single] if isinstance(single, dict) else []
    if not results:
        return None

    n = len(results)
    completed = sum(1 for r in results if (r.get("score") or {}).get("completed"))
    trace_passed = sum(1 for r in results if (r.get("trace_verdict") or {}).get("passed"))
    total_tokens = sum(int((r.get("score") or {}).get("total_tokens") or 0) for r in results)
    fitness = [
        _as_float((r.get("score") or {}).get("fitness_score"))
        for r in results
        if (r.get("score") or {}).get("fitness_score") is not None
    ]
    tool_rates = [
        _as_float((r.get("trace_verdict") or {}).get("tool_success_rate"))
        for r in results
        if (r.get("trace_verdict") or {}).get("tool_success_rate") is not None
    ]
    avg_tokens = total_tokens / max(n, 1)
    return {
        "run_id": candidate_dir.parents[1].name,
        "candidate_id": candidate_dir.name,
        "scenarios_evaluated": n,
        "completion_rate": round(completed / max(n, 1), 4),
        "trace_gate_pass_rate": round(trace_passed / max(n, 1), 4),
        "avg_turns": round(sum(int(r.get("turns") or 1) for r in results) / max(n, 1), 3),
        "turn_efficiency": round(1.0 / max(sum(int(r.get("turns") or 1) for r in results) / max(n, 1), 1.0), 4),
        "tool_success_rate": round(sum(tool_rates) / len(tool_rates), 4)
        if tool_rates
        else 1.0,
        "memory_utilization_rate": round(
            sum(1 for r in results if (r.get("score") or {}).get("memory_utilization"))
            / max(n, 1),
            4,
        ),
        "fitness_score": round(sum(fitness) / len(fitness), 4) if fitness else 0.0,
        "total_tokens": total_tokens,
        "avg_tokens": round(avg_tokens, 1),
        "token_efficiency": round(1000.0 / max(avg_tokens, 1.0), 6),
    }


def _load_meta_harness_candidates(seen: set[str]) -> list[dict[str, Any]]:
    """Load Feature-016 candidate runs from data/meta_harness."""
    if not META_HARNESS_RUNS_DIR.exists():
        return []

    candidates: list[dict[str, Any]] = []
    for candidate_dir in sorted(META_HARNESS_RUNS_DIR.glob("*/candidates/*")):
        if not candidate_dir.is_dir():
            continue
        run_id = candidate_dir.parents[1].name
        candidate_id = candidate_dir.name
        version = f"{run_id}:{candidate_id}"
        if version in seen:
            continue

        aggregate = _load_json(candidate_dir / "aggregate.json")
        if not isinstance(aggregate, dict):
            aggregate = _fallback_meta_aggregate(candidate_dir)
        if not isinstance(aggregate, dict):
            continue

        entry = dict(aggregate)
        entry["version"] = version
        entry["run_id"] = run_id
        entry["candidate_id"] = candidate_id
        entry["candidate_path"] = str(candidate_dir)
        entry["source"] = "meta_harness"
        entry = _normalize_candidate(entry)
        seen.add(version)
        candidates.append(entry)

    return candidates


def _load_candidates_db(seen: set[str]) -> list[dict[str, Any]]:
    """Load candidates from agent.component_configs."""
    import os

    import psycopg

    db_url = os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )
    candidates = []
    with psycopg.connect(db_url, autocommit=True) as conn:
        rows = conn.execute(
            """
            SELECT version, label, stage, config, notes,
                   proposer_model, pareto_frontier, created_at
            FROM agent.component_configs
            WHERE component_id = 'harness.default'
            ORDER BY version ASC
            """,
        ).fetchall()
        for row in rows:
            version, label, stage, config, notes, model, frontier, created = row
            version_label = label or f"v{version:03d}"
            if version_label in seen:
                continue
            seen.add(version_label)
            entry: dict[str, Any] = {
                "version": version_label,
                "db_version": version,
                "stage": stage,
                "proposer_model": model,
                "pareto_frontier": frontier,
                "source": "db",
            }
            # Merge config fields if they look like score data
            if isinstance(config, dict):
                for k in (
                    "trace_gate_pass_rate",
                    "completion_rate",
                    "avg_turns",
                    "total_tokens",
                    "tool_success_rate",
                    "memory_utilization_rate",
                    "fitness_score",
                    "total_cost_usd",
                ):
                    if k in config:
                        entry[k] = config[k]
            candidates.append(_normalize_candidate(entry))
    return candidates


def _load_candidates_fs(seen: set[str]) -> list[dict[str, Any]]:
    """Load scored candidates from data/harness/candidates/ (filesystem)."""
    if not CANDIDATES_DIR.exists():
        return []

    candidates = []
    for version_dir in sorted(CANDIDATES_DIR.glob("v*")):
        if version_dir.name in seen:
            continue

        scores_path = version_dir / "scores.json"
        config_path = version_dir / "config.json"

        if not scores_path.exists():
            continue

        scores = json.loads(scores_path.read_text(encoding="utf-8"))
        scores["version"] = version_dir.name
        scores["source"] = "filesystem"

        if config_path.exists():
            scores["has_config"] = True

        seen.add(version_dir.name)
        candidates.append(_normalize_candidate(scores))

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
                "source": c.get("source", ""),
                "candidate_path": c.get("candidate_path", ""),
                "trace_gate_pass_rate": c.get("trace_gate_pass_rate", 0),
                "completion_rate": c.get("completion_rate", 0),
                "fitness_score": c.get("fitness_score", 0),
                "feasible": c.get("feasible", False),
                "feasibility_failures": c.get("feasibility_failures", []),
                "avg_turns": c.get("avg_turns", 0),
                "tool_success_rate": c.get("tool_success_rate", 0),
                "memory_utilization_rate": c.get("memory_utilization_rate", 0),
                "total_tokens": c.get("total_tokens", 0),
                "token_efficiency": c.get("token_efficiency", 0),
                "cost_usd": c.get("total_cost_usd", 0),
                "cost_efficiency": c.get("cost_efficiency", 0),
                "avg_duration_ms": c.get("avg_duration_ms", 0),
                "latency_efficiency": c.get("latency_efficiency", 0),
            }
            for c in frontier
        ],
        "dominated": [c.get("version", "") for c in candidates if c not in frontier],
    }
