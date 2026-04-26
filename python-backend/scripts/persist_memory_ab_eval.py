"""Persist one memory A/B result into `agent.evals`.

Usage:
  uv run python scripts/persist_memory_ab_eval.py result.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from meta_harness.evals_store import save_memory_ab_eval


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: uv run python scripts/persist_memory_ab_eval.py result.json")
        return 2

    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    run_id = save_memory_ab_eval(
        corpus_id=data["corpus_id"],
        queries=data["queries"],
        hindsight_metrics=data["hindsight"],
        mempalace_metrics=data["mempalace"],
        name=data.get("name"),
    )
    print(run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
