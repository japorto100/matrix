"""Aggregate Hindsight + MemPalace result JSONs into one memory_ab comparison.

Input schema per file:
{
  "pipeline": "hindsight" | "mempalace",
  "corpus_id": "sample-corpus",
  "items": [
    {
      "query": "What did the agent say about Brent?",
      "expected_ids": ["m1", "m2"],
      "retrieved_ids": ["m2", "m9"],
      "latency_ms": 123.4,
      "token_cost": 0.0012,
      "error": null
    }
  ]
}

Usage:
  uv run python experiments/memory_eval/aggregate_memory_ab.py \
    hindsight.json mempalace.json --out result.json [--persist]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from experiments.memory_eval.metrics import summarize_eval_run


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _summarize(run: dict[str, Any]) -> dict[str, Any]:
    return summarize_eval_run(run)


def build_memory_ab(hindsight: dict[str, Any], mempalace: dict[str, Any]) -> dict[str, Any]:
    corpus_id = hindsight.get("corpus_id") or mempalace.get("corpus_id") or "unknown"
    queries = [
        str(item.get("query") or "")
        for item in hindsight.get("items", [])
        if item.get("query")
    ]
    return {
        "name": f"memory_ab:{corpus_id}",
        "corpus_id": corpus_id,
        "queries": queries,
        "hindsight": _summarize(hindsight),
        "mempalace": _summarize(mempalace),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("hindsight")
    parser.add_argument("mempalace")
    parser.add_argument("--out", required=True)
    parser.add_argument("--persist", action="store_true")
    args = parser.parse_args()

    h = _load(Path(args.hindsight))
    m = _load(Path(args.mempalace))
    result = build_memory_ab(h, m)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.persist:
        from agent.harness.evals_store import save_memory_ab_eval

        run_id = save_memory_ab_eval(
            corpus_id=result["corpus_id"],
            queries=result["queries"],
            hindsight_metrics=result["hindsight"],
            mempalace_metrics=result["mempalace"],
            name=result["name"],
        )
        print(run_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
