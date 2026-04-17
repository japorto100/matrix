"""Run retrieval evaluation against the Hindsight + MemPalace fusion layer."""

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

from memory_fusion import FusionMemoryEngine  # noqa: E402
from memory_fusion.query_gate import decide_query_path  # noqa: E402


async def _run_one(
    *,
    engine: FusionMemoryEngine,
    bank_id: str,
    query: str,
    expected_ids: list[str],
    expected_refs: list[str],
    fact_types: list[str] | None = None,
    category: str | None = None,
    expected_substring: str = "",
) -> dict[str, Any]:
    start = time.perf_counter()
    query_gate = decide_query_path(query, query)
    try:
        from hindsight_api.models import RequestContext

        results = await engine.recall(
            bank_id=bank_id,
            query=query,
            fact_type=fact_types,
            n_results=10,
            request_context=RequestContext(),
            consumer="admin_debug",
        )
    except Exception as e:  # noqa: BLE001
        return {
            "query": query,
            "expected_ids": expected_ids,
            "expected_refs": expected_refs,
            "retrieved_ids": [],
            "retrieved_refs": [],
            "retrieved_layers": [],
            "retrieved_source_types": [],
            "retrieved_artifact_types": [],
            "retrieved_statuses": [],
            "retrieved_provenance": [],
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "token_cost": 0.0,
            "category": category,
            "error": str(e),
            "expected_substring": expected_substring,
            "needs_verification": query_gate.needs_verification,
        }

    retrieved_refs = [item.ref for item in results]
    primary_ids = retrieved_refs if expected_refs else retrieved_refs
    return {
        "query": query,
        "expected_ids": expected_refs or expected_ids,
        "expected_refs": expected_refs,
        "retrieved_ids": primary_ids,
        "retrieved_refs": retrieved_refs,
        "retrieved_texts": [item.text for item in results[:5]],
        "retrieved_layers": [str(item.metadata.get("memory_layer") or "") for item in results[:5]],
        "retrieved_source_types": [str(item.metadata.get("source_type") or "") for item in results[:5]],
        "retrieved_artifact_types": [str(item.metadata.get("artifact_type") or "") for item in results[:5]],
        "retrieved_statuses": [str(item.metadata.get("status") or "") for item in results[:10]],
        "retrieved_provenance": [str(item.metadata.get("provenance_ref") or item.metadata.get("source_ref") or "") for item in results[:10]],
        "providers": [item.providers for item in results[:10]],
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        "token_cost": 0.0,
        "category": category,
        "error": None,
        "expected_substring": expected_substring,
        "needs_verification": query_gate.needs_verification,
    }


async def run_eval(input_path: Path, output_path: Path, *, db_url: str | None, palace_path: str | None) -> None:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    engine = await FusionMemoryEngine.create(db_url=db_url, palace_path=palace_path)

    out = {
        "pipeline": "fusion",
        "corpus_id": data.get("corpus_id", "unknown"),
        "items": [],
    }
    bank_id = str(data["bank_id"])
    for item in data.get("queries", []):
        out["items"].append(
            await _run_one(
                engine=engine,
                bank_id=bank_id,
                query=str(item.get("query") or ""),
                expected_ids=list(item.get("expected_ids") or []),
                expected_refs=list(item.get("expected_refs") or []),
                fact_types=list(item.get("fact_types") or []) or None,
                category=str(item.get("category") or "") or None,
                expected_substring=str(item.get("expected_substring") or item.get("answer") or ""),
            )
        )
    output_path.write_text(json.dumps(out, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--db-url")
    parser.add_argument("--palace-path")
    args = parser.parse_args()
    asyncio.run(
        run_eval(
            Path(args.input_json),
            Path(args.out),
            db_url=args.db_url,
            palace_path=args.palace_path,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
