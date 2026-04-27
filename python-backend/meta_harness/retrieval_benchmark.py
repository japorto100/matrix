"""Meta-Harness artifact writer for retrieval benchmark candidates."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from meta_harness.config import capture_current_config
from meta_harness.proposer import META_HARNESS_DATA_DIR
from retrieval.evals.benchmark_lab import (
    DEFAULT_MATRIX_CANDIDATES,
    RetrievalCandidate,
    compare_candidates,
)
from retrieval.evals.canaries import (
    DEFAULT_SEARCH_CANARIES,
    RetrievalCanary,
)

DEFAULT_RETRIEVAL_CANARIES = DEFAULT_SEARCH_CANARIES

REQUIRED_CANDIDATE_METADATA = (
    "source_corpus",
    "parser_version",
    "chunker_version",
    "embedding_model",
    "embedding_dimension",
    "kg_projection_version",
)


async def run_retrieval_benchmark(
    *,
    run_id: str | None = None,
    canaries: tuple[RetrievalCanary, ...] = DEFAULT_RETRIEVAL_CANARIES,
    candidates: tuple[RetrievalCandidate, ...] = DEFAULT_MATRIX_CANDIDATES,
    data_dir: Path = META_HARNESS_DATA_DIR,
    k: int = 5,
    token_budget: int = 1600,
    max_hits: int = 8,
) -> dict[str, Any]:
    """Run retrieval candidates and write Pareto-readable Meta-Harness artifacts."""

    run_id = run_id or f"run-rag-kg-{uuid.uuid4().hex[:12]}"
    report = await compare_candidates(
        canaries,
        candidates=candidates,
        k=k,
        token_budget=token_budget,
        max_hits=max_hits,
    )
    written = write_retrieval_benchmark_artifacts(
        report,
        run_id=run_id,
        data_dir=data_dir,
    )
    return {"run_id": run_id, "report": report, "artifacts": written}


def write_retrieval_benchmark_artifacts(
    report: dict[str, Any],
    *,
    run_id: str,
    data_dir: Path = META_HARNESS_DATA_DIR,
) -> dict[str, Any]:
    """Write one candidate directory per retrieval mode in a benchmark report."""

    run_dir = data_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "kind": "retrieval_benchmark",
        "feature_id": report.get("feature_id", "022"),
        "scenario_set": "matrix-retrieval-canaries@2026-04-27",
        "splits": report.get("splits", []),
        "holdout_protected": "holdout" not in set(report.get("splits", [])),
        "stack": {
            "python_agent": True,
            "frontend_required": False,
            "go_gateway_required": False,
            "postgres_required": True,
            "litellm_base_url": os.environ.get("LITELLM_BASE_URL", ""),
            "embedding_provider": os.environ.get("EMBEDDER_PROVIDER")
            or os.environ.get("MEMORY_EMBEDDING_PROVIDER", ""),
            "embedding_model": os.environ.get("EMBEDDER_MODEL")
            or os.environ.get("MEMORY_EMBEDDING_MODEL", ""),
        },
    }
    (run_dir / "run.json").write_text(
        json.dumps(run_manifest, indent=2, default=str),
        encoding="utf-8",
    )

    written: list[dict[str, Any]] = []
    for candidate in report.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(candidate.get("candidate_id") or "unknown")
        candidate_dir = run_dir / "candidates" / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_report = {
            "generated_at": report.get("generated_at"),
            "feature_id": report.get("feature_id"),
            "k": report.get("k"),
            "token_budget": report.get("token_budget"),
            "max_hits": report.get("max_hits"),
            "canary_count": report.get("canary_count"),
            "splits": report.get("splits", []),
            "question_classes": report.get("question_classes", []),
            "metadata_compatibility": _metadata_compatibility(candidate),
            "candidate": candidate,
        }
        aggregate = _candidate_aggregate(run_id, candidate)
        verdicts = _candidate_verdicts(candidate)

        _write_json(candidate_dir / "retrieval_benchmark.json", candidate_report)
        _write_json(candidate_dir / "aggregate.json", aggregate)
        _write_json(candidate_dir / "scores.json", aggregate)
        _write_json(candidate_dir / "verdicts.json", verdicts)
        _write_json(candidate_dir / "scenario_set.json", _scenario_set(candidate))
        _write_json(candidate_dir / "config.json", _config_snapshot())
        _write_json(candidate_dir / "source_snapshot.json", _source_snapshot())
        written.append(
            {
                "candidate_id": candidate_id,
                "candidate_path": str(candidate_dir),
                "pass_rate": candidate.get("pass_rate"),
                "fitness_score": aggregate["fitness_score"],
            }
        )

    return {"run_path": str(run_dir), "candidates": written}


def _candidate_aggregate(run_id: str, candidate: dict[str, Any]) -> dict[str, Any]:
    count = int(candidate.get("count") or 0)
    pass_rate = _as_float(candidate.get("pass_rate"))
    recall = _as_float(candidate.get("recall@5"))
    ndcg = _as_float(candidate.get("ndcg@5"))
    latency_ms = _as_float(candidate.get("latency_ms_avg"))
    fitness = round((pass_rate * 0.5) + (recall * 0.3) + (ndcg * 0.2), 4)
    return {
        "run_id": run_id,
        "candidate_id": candidate.get("candidate_id", ""),
        "benchmark_type": "rag_kg_retrieval",
        "scenarios_evaluated": count,
        "completion_rate": 1.0 if count else 0.0,
        "trace_gate_pass_rate": pass_rate,
        "tool_success_rate": 1.0,
        "memory_utilization_rate": 0.0,
        "fitness_score": fitness,
        "retrieval_pass_rate": pass_rate,
        "recall@5": recall,
        "ndcg@5": ndcg,
        "avg_turns": 1.0,
        "turn_efficiency": 1.0,
        "total_tokens": 0,
        "avg_tokens": 0.0,
        "token_efficiency": 1000.0,
        "total_cost_usd": 0.0,
        "avg_cost_usd": 0.0,
        "cost_efficiency": 1.0,
        "avg_duration_ms": latency_ms,
        "total_duration_ms": round(latency_ms * max(count, 1), 3),
        "latency_efficiency": round(1000.0 / max(latency_ms, 1.0), 6)
        if latency_ms > 0
        else 1.0,
        "failed_scenarios": [
            {
                "scenario_id": result.get("canary_id"),
                "failures": result.get("failures", []),
            }
            for result in candidate.get("results", [])
            if isinstance(result, dict) and not result.get("passed")
        ],
    }


def _candidate_verdicts(candidate: dict[str, Any]) -> dict[str, Any]:
    failures = [
        f"{result.get('canary_id')}: {', '.join(result.get('failures') or [])}"
        for result in candidate.get("results", [])
        if isinstance(result, dict) and not result.get("passed")
    ]
    compatibility = _metadata_compatibility(candidate)
    failures.extend(compatibility["failures"])
    return {
        "passed": not failures,
        "failures": failures,
        "metadata_compatibility": compatibility,
        "observed_actions": ["retrieval_benchmark"],
        "observed_tools": [],
        "tool_success_rate": 1.0,
    }


def _metadata_compatibility(candidate: dict[str, Any]) -> dict[str, Any]:
    metadata = candidate.get("metadata") if isinstance(candidate, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    missing = [
        key
        for key in REQUIRED_CANDIDATE_METADATA
        if metadata.get(key) in (None, "")
    ]
    failures = [f"missing-candidate-metadata:{key}" for key in missing]
    return {
        "passed": not failures,
        "required_keys": list(REQUIRED_CANDIDATE_METADATA),
        "missing_keys": missing,
        "failures": failures,
    }


def _scenario_set(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenarios": [
            {
                "id": result.get("canary_id"),
                "query": result.get("query", ""),
                "split": result.get("split", ""),
                "question_class": result.get("question_class", ""),
                "ranked_reference_ids": result.get("ranked_reference_ids", []),
            }
            for result in candidate.get("results", [])
            if isinstance(result, dict)
        ]
    }


def _config_snapshot() -> dict[str, Any]:
    try:
        return json.loads(capture_current_config().to_json())
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _source_snapshot() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    paths = [
        "python-backend/retrieval/api.py",
        "python-backend/retrieval/evals/benchmark_lab.py",
        "python-backend/retrieval/evals/canaries.py",
        "python-backend/meta_harness/retrieval_benchmark.py",
        "python-backend/meta_harness/proposer.py",
        "python-backend/meta_harness/pareto.py",
    ]
    files = []
    for rel in paths:
        path = root / rel
        if not path.exists():
            continue
        files.append({"path": rel, "bytes": path.stat().st_size})
    return {"files": files}


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
