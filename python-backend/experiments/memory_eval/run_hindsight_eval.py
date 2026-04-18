# ruff: noqa: E402
"""Run retrieval evaluation against an existing Hindsight bank.

Input schema:
{
  "corpus_id": "sample-corpus",
  "bank_id": "user_local",
  "source_root": "../fixtures/convos",   // optional
  "queries": [
    {
      "query": "What did the agent say about Brent?",
      "expected_ids": ["m1", "m2"],
      "expected_refs": ["session-01.jsonl#0"]
    }
  ]
}

Output schema matches `aggregate_memory_ab.py` expectations for pipeline=hindsight.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_fusion.engine import get_memory_engine
from memory_fusion.query_gate import decide_query_path


def _resolve_path(value: str | None, *, base_dir: Path) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _normalize_source_ref(meta: dict[str, Any], *, source_root: Path | None) -> str:
    source_ref = str(meta.get("source_ref") or "").strip()
    if source_ref:
        return source_ref

    source_file = str(meta.get("source_path") or meta.get("source_file") or "?")
    chunk_id = str(meta.get("chunk_id") or meta.get("document_id") or "?")
    source_path = Path(source_file).expanduser()
    try:
        source_path = source_path.resolve()
    except OSError:
        pass

    ref_path: Path | str = source_path
    if source_root is not None:
        try:
            ref_path = source_path.relative_to(source_root.resolve())
        except (OSError, ValueError):
            ref_path = source_path
    else:
        ref_path = source_path.name

    ref_text = ref_path.as_posix() if isinstance(ref_path, Path) else str(ref_path)
    return f"{ref_text}#{chunk_id}"


async def _run_one(
    *,
    bank_id: str,
    query: str,
    expected_ids: list[str],
    expected_refs: list[str],
    source_root: Path | None,
    expected_substring: str = "",
) -> dict[str, Any]:
    expected = expected_refs or expected_ids
    engine = await get_memory_engine()
    query_gate = decide_query_path(query, query)
    if engine is None:
        return {
            "query": query,
            "expected_ids": expected,
            "expected_refs": expected_refs,
            "retrieved_ids": [],
            "retrieved_refs": [],
            "retrieved_texts": [],
            "retrieved_statuses": [],
            "retrieved_provenance": [],
            "latency_ms": None,
            "token_cost": 0.0,
            "error": "memory engine unavailable",
            "expected_substring": expected_substring,
            "needs_verification": query_gate.needs_verification,
        }

    from hindsight_api.engine.memory_engine import Budget
    from hindsight_api.models import RequestContext

    start = time.perf_counter()
    try:
        result = await engine.recall_async(
            bank_id=bank_id,
            query=query,
            fact_type=["world", "experience", "observation"],
            budget=Budget.MID,
            max_tokens=2000,
            request_context=RequestContext(),
        )
    except Exception as e:  # noqa: BLE001
        return {
            "query": query,
            "expected_ids": expected,
            "expected_refs": expected_refs,
            "retrieved_ids": [],
            "retrieved_refs": [],
            "retrieved_texts": [],
            "retrieved_statuses": [],
            "retrieved_provenance": [],
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "token_cost": 0.0,
            "error": str(e),
            "expected_substring": expected_substring,
            "needs_verification": query_gate.needs_verification,
        }

    retrieved_refs = [
        _normalize_source_ref(getattr(f, "metadata", {}) or {}, source_root=source_root)
        for f in result.results[:10]
    ]
    primary_ids = retrieved_refs if expected_refs else [getattr(f, "id", "") for f in result.results[:10]]

    return {
        "query": query,
        "expected_ids": expected,
        "expected_refs": expected_refs,
        "retrieved_ids": primary_ids,
        "retrieved_refs": retrieved_refs,
        "retrieved_raw_ids": [getattr(f, "id", "") for f in result.results[:10]],
        "retrieved_texts": [getattr(f, "text", "") for f in result.results[:5]],
        "retrieved_statuses": [str((getattr(f, "metadata", {}) or {}).get("status") or "") for f in result.results[:10]],
        "retrieved_provenance": [
            str((getattr(f, "metadata", {}) or {}).get("provenance_ref") or (getattr(f, "metadata", {}) or {}).get("source_ref") or "")
            for f in result.results[:10]
        ],
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        "token_cost": 0.0,
        "error": None,
        "expected_substring": expected_substring,
        "needs_verification": query_gate.needs_verification,
    }


async def run_eval(input_path: Path, output_path: Path) -> None:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    bank_id = data["bank_id"]
    source_root = _resolve_path(
        str(data.get("source_root") or ""),
        base_dir=input_path.parent,
    )
    out = {
        "pipeline": "hindsight",
        "corpus_id": data.get("corpus_id", "unknown"),
        "items": [],
    }

    for item in data.get("queries", []):
        result = await _run_one(
            bank_id=bank_id,
            query=str(item.get("query") or ""),
            expected_ids=list(item.get("expected_ids") or []),
            expected_refs=list(item.get("expected_refs") or []),
            source_root=source_root,
            expected_substring=str(item.get("expected_substring") or item.get("answer") or ""),
        )
        out["items"].append(result)

    output_path.write_text(json.dumps(out, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    asyncio.run(run_eval(Path(args.input_json), Path(args.out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
