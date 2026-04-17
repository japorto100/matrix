"""Convert MemoryArena-style tasks into the shared memory-eval schema.

Erwarteter Input:
- JSON oder JSONL mit Tasks im Stil:
  - `id`
  - `questions`: list[str]
  - `answers`: list[str]
  - `backgrounds`: str | list[str] | optional

Der Adapter baut fuer jeden Task fortlaufende Session-Memory-Schnipsel:
- Background (falls vorhanden)
- fruehere Fragen/Antworten als bereits bekannte Historie
- aktuelle Frage wird als Eval-Query ausgegeben
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_input(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return list(data["data"])
    raise ValueError("Unsupported MemoryArena input format")


def _background_for_step(backgrounds: Any, idx: int) -> str:
    if isinstance(backgrounds, list):
        if idx < len(backgrounds):
            return str(backgrounds[idx] or "").strip()
        if backgrounds:
            return str(backgrounds[-1] or "").strip()
        return ""
    return str(backgrounds or "").strip()


def convert_memoryarena(
    tasks: list[dict[str, Any]],
    *,
    corpus_id: str,
    bank_id: str,
    category: str,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []

    for task in tasks:
        task_id = str(task.get("id") or len(items))
        questions = [str(value).strip() for value in list(task.get("questions") or [])]
        answers = [str(value).strip() for value in list(task.get("answers") or [])]
        backgrounds = task.get("backgrounds")

        history: list[str] = []
        for idx, question in enumerate(questions):
            answer = answers[idx] if idx < len(answers) else ""
            background = _background_for_step(backgrounds, idx)
            source_ref = f"memoryarena-{task_id}.jsonl#{idx}"

            memory_parts = [part for part in [background, *history] if part]
            if answer:
                memory_parts.append(f"Known answer for subtask {idx}: {answer}")

            items.append(
                {
                    "source_ref": source_ref,
                    "source_file": f"memoryarena-{task_id}.jsonl",
                    "text": "\n".join(memory_parts),
                    "fact_type": "experience",
                    "tags": ["memoryarena", category, f"task:{task_id}"],
                }
            )
            queries.append(
                {
                    "query": question,
                    "expected_refs": [source_ref],
                    "expected_substring": answer,
                    "category": category,
                    "task_id": task_id,
                    "step_index": idx,
                }
            )

            history.append(f"Question {idx}: {question}")
            if answer:
                history.append(f"Answer {idx}: {answer}")

    return {
        "corpus_id": corpus_id,
        "bank_id": bank_id,
        "items": items,
        "queries": queries,
    }


def _materialize_input(path_value: str, *, download_url: str | None, cache_dir: str | None) -> Path:
    path = Path(path_value).expanduser()
    if path.exists():
        return path
    if not download_url:
        raise FileNotFoundError(f"MemoryArena input not found: {path}")
    target_dir = Path(cache_dir or ".tmp/memory_eval_downloads").expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    urllib.request.urlretrieve(download_url, target)  # noqa: S310 - explicit user-provided dataset URL
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("--out", required=True)
    parser.add_argument("--corpus-id", default="memoryarena-adapter")
    parser.add_argument("--bank-id", default="user_eval_memoryarena")
    parser.add_argument("--category", default="memoryarena")
    parser.add_argument("--download-url")
    parser.add_argument("--cache-dir")
    args = parser.parse_args()

    input_path = _materialize_input(
        args.input_path,
        download_url=args.download_url,
        cache_dir=args.cache_dir,
    )
    tasks = _load_input(input_path)
    converted = convert_memoryarena(
        tasks,
        corpus_id=args.corpus_id,
        bank_id=args.bank_id,
        category=args.category,
    )
    Path(args.out).write_text(json.dumps(converted, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
