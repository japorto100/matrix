# ruff: noqa: E402
"""Aggregate multiple memory pipeline runs (e.g. hindsight, mempalace, fusion)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.memory_eval.aggregate_memory_ab import _summarize


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_suite(runs: list[dict[str, Any]]) -> dict[str, Any]:
    corpus_id = next((run.get("corpus_id") for run in runs if run.get("corpus_id")), "unknown")
    pipelines = {}
    out: dict[str, Any] = {
        "name": f"memory_suite:{corpus_id}",
        "corpus_id": corpus_id,
        "pipelines": pipelines,
    }
    for run in runs:
        name = str(run.get("pipeline") or "unknown")
        pipelines[name] = _summarize(run)
    out["leaderboard"] = sorted(
        (
            {
                "pipeline": name,
                "mean_recall": metrics.get("mean_recall", 0.0),
                "evidence_hit_rate": metrics.get("quality", {}).get("evidence_hit_rate", 0.0),
                "candidate_leak_rate": metrics.get("governance", {}).get("candidate_leak_rate", 0.0),
                "mean_latency_ms": metrics.get("mean_latency_ms", 0.0),
            }
            for name, metrics in pipelines.items()
        ),
        key=lambda row: (
            -float(row["mean_recall"]),
            -float(row["evidence_hit_rate"]),
            float(row["candidate_leak_rate"]),
            float(row["mean_latency_ms"]),
        ),
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    runs = [_load(Path(path)) for path in args.runs]
    result = build_suite(runs)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
