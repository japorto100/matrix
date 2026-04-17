"""Run retrieval evaluation against a real MemPalace palace or convo corpus.

Input schema:
{
  "corpus_id": "sample-corpus",
  "palace_path": ".tmp/mempalace_eval/sample-corpus",   // optional
  "convo_dir": "../fixtures/convos",                    // optional
  "source_root": "../fixtures/convos",                  // optional ref normalization root
  "wing": "sample",                                     // optional default wing
  "room": "planning",                                   // optional default room filter
  "extract_mode": "exchange",                           // optional: exchange|general
  "remine": false,                                      // optional: rebuild palace from convo_dir
  "queries": [
    {
      "query": "What did the agent say about Brent?",
      "expected_ids": ["drawer_sample_planning_..."],   // optional
      "expected_refs": ["session-a.jsonl#0"],           // optional canonical refs
      "wing": "sample",                                 // optional per-query override
      "room": "planning",                               // optional per-query override
      "n_results": 10
    }
  ]
}

If `expected_refs` is provided, the runner emits normalized `retrieved_ids` in the
same `source_file#chunk_index` format so `aggregate_memory_ab.py` can score the
run without depending on MemPalace's internal drawer IDs. Raw drawer IDs remain
available in `retrieved_drawer_ids`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from memory_fusion.query_gate import decide_query_path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _mempalace_root() -> Path:
    return _repo_root() / "_ref" / "mempalace"


def _ensure_mempalace_on_path() -> None:
    root = _mempalace_root()
    if not root.exists():
        raise RuntimeError(
            "MemPalace submodule missing. Run: git submodule update --init --recursive"
        )
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _resolve_path(value: str | None, *, base_dir: Path) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _safe_slug(value: str) -> str:
    text = (value or "memory-eval").strip().lower()
    cleaned = [ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in text]
    return "".join(cleaned).strip("_") or "memory-eval"


def _default_palace_path(corpus_id: str) -> Path:
    return _repo_root() / "python-backend" / ".tmp" / "mempalace_eval" / _safe_slug(corpus_id)


def _normalize_source_ref(meta: dict[str, Any], *, source_root: Path | None) -> str:
    source_ref = str(meta.get("source_ref") or "").strip()
    if source_ref:
        return source_ref

    source_file = str(meta.get("source_file") or "?")
    chunk_index = meta.get("chunk_id", meta.get("chunk_index"))
    source_path = Path(source_file).expanduser()

    try:
        source_path = source_path.resolve()
    except OSError:
        pass

    ref_path: Path | str = source_path
    if source_root is not None:
        try:
            root = source_root.resolve()
            ref_path = source_path.relative_to(root)
        except (OSError, ValueError):
            ref_path = source_path
    else:
        ref_path = source_path.name

    ref_text = ref_path.as_posix() if isinstance(ref_path, Path) else str(ref_path)
    suffix = "?" if chunk_index is None else str(chunk_index)
    return f"{ref_text}#{suffix}"


def _prepare_palace(
    data: dict[str, Any],
    *,
    base_dir: Path,
    force_remine: bool,
) -> Path:
    _ensure_mempalace_on_path()

    corpus_id = str(data.get("corpus_id") or "memory-eval")
    palace_path = _resolve_path(str(data.get("palace_path") or ""), base_dir=base_dir)
    if palace_path is None:
        palace_path = _default_palace_path(corpus_id)

    convo_dir = _resolve_path(str(data.get("convo_dir") or ""), base_dir=base_dir)
    remine = bool(data.get("remine")) or force_remine

    if convo_dir is not None:
        if not convo_dir.exists():
            raise FileNotFoundError(f"MemPalace convo_dir not found: {convo_dir}")

        if remine and palace_path.exists():
            shutil.rmtree(palace_path, ignore_errors=True)

        if remine or not palace_path.exists():
            from mempalace.convo_miner import mine_convos

            extract_mode = str(data.get("extract_mode") or "exchange")
            wing = str(data.get("wing") or convo_dir.name.lower().replace(" ", "_"))
            palace_path.parent.mkdir(parents=True, exist_ok=True)
            mine_convos(
                str(convo_dir),
                palace_path=str(palace_path),
                wing=wing,
                extract_mode=extract_mode,
            )

    if not palace_path.exists():
        raise FileNotFoundError(
            f"MemPalace palace not found: {palace_path}. Provide palace_path or convo_dir."
        )

    return palace_path


def _run_query(
    *,
    palace_path: Path,
    query: str,
    wing: str | None,
    room: str | None,
    n_results: int,
) -> tuple[list[str], list[str], list[dict[str, Any]], list[float]]:
    _ensure_mempalace_on_path()

    from mempalace.palace import get_collection
    from mempalace.searcher import build_where_filter

    collection = get_collection(str(palace_path), create=False)
    where = build_where_filter(wing, room)
    kwargs: dict[str, Any] = {
        "query_texts": [query],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    result = collection.query(**kwargs)
    return (
        list(result.get("ids", [[]])[0]),
        list(result.get("documents", [[]])[0]),
        list(result.get("metadatas", [[]])[0]),
        list(result.get("distances", [[]])[0]),
    )


def _run_one(
    *,
    palace_path: Path,
    source_root: Path | None,
    defaults: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any]:
    query = str(item.get("query") or "")
    expected_refs = list(item.get("expected_refs") or [])
    expected_ids = expected_refs or list(item.get("expected_ids") or [])
    wing = item.get("wing", defaults.get("wing"))
    room = item.get("room", defaults.get("room"))
    n_results = int(item.get("n_results") or defaults.get("n_results") or 10)
    query_gate = decide_query_path(query, query)

    start = time.perf_counter()
    try:
        drawer_ids, documents, metadatas, distances = _run_query(
            palace_path=palace_path,
            query=query,
            wing=str(wing) if wing else None,
            room=str(room) if room else None,
            n_results=n_results,
        )
    except Exception as e:  # noqa: BLE001
        return {
            "query": query,
            "expected_ids": expected_ids,
            "expected_refs": expected_refs,
            "retrieved_ids": [],
            "retrieved_drawer_ids": [],
            "retrieved_refs": [],
            "retrieved_statuses": [],
            "retrieved_provenance": [],
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "token_cost": 0.0,
            "error": str(e),
            "wing": wing,
            "room": room,
            "needs_verification": query_gate.needs_verification,
        }

    retrieved_refs = [
        _normalize_source_ref(meta or {}, source_root=source_root) for meta in metadatas
    ]
    primary_ids = retrieved_refs if expected_refs else drawer_ids

    return {
        "query": query,
        "expected_ids": expected_ids,
        "expected_refs": expected_refs,
        "retrieved_ids": primary_ids,
        "retrieved_drawer_ids": drawer_ids,
        "retrieved_refs": retrieved_refs,
        "retrieved_texts": documents[:5],
        "retrieved_statuses": [str((meta or {}).get("status") or "available") for meta in metadatas[:10]],
        "retrieved_provenance": [
            str((meta or {}).get("source_ref") or _normalize_source_ref(meta or {}, source_root=source_root))
            for meta in metadatas[:10]
        ],
        "distances": [round(float(dist), 4) for dist in distances[:10]],
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        "token_cost": 0.0,
        "error": None,
        "wing": wing,
        "room": room,
        "expected_substring": str(item.get("expected_substring") or item.get("answer") or ""),
        "needs_verification": query_gate.needs_verification,
    }


def run_eval(input_path: Path, output_path: Path, *, force_remine: bool = False) -> None:
    data = json.loads(input_path.read_text(encoding="utf-8"))
    base_dir = input_path.parent
    palace_path = _prepare_palace(data, base_dir=base_dir, force_remine=force_remine)
    source_root = _resolve_path(
        str(data.get("source_root") or data.get("convo_dir") or ""),
        base_dir=base_dir,
    )

    defaults = {
        "wing": data.get("wing"),
        "room": data.get("room"),
        "n_results": data.get("n_results", 10),
    }

    out = {
        "pipeline": "mempalace",
        "corpus_id": data.get("corpus_id", "unknown"),
        "palace_path": str(palace_path),
        "items": [],
    }

    for item in data.get("queries", []):
        result = _run_one(
            palace_path=palace_path,
            source_root=source_root,
            defaults=defaults,
            item=dict(item),
        )
        out["items"].append(result)

    output_path.write_text(json.dumps(out, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--remine",
        action="store_true",
        help="Rebuild the MemPalace index from convo_dir before running the eval.",
    )
    args = parser.parse_args()

    run_eval(Path(args.input_json), Path(args.out), force_remine=args.remine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
