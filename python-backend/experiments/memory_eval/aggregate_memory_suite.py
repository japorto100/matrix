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
    out: dict[str, Any] = {
        "name": f"memory_suite:{corpus_id}",
        "corpus_id": corpus_id,
        "pipelines": {},
    }
    for run in runs:
        name = str(run.get("pipeline") or "unknown")
        out["pipelines"][name] = _summarize(run)
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
