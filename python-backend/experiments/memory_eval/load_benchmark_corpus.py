"""Load a small shared corpus into Hindsight and/or MemPalace.

This gives both systems the same input records and canonical `source_ref`
metadata so later evals and fusion runs compare like with like.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory_fusion.fusion_engine import FusionMemoryEngine  # noqa: E402
from memory_fusion.providers import (  # noqa: E402
    create_hindsight_engine,
    create_mempalace_engine,
)


def _resolve_path(value: str | None, *, base_dir: Path) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


async def _load_hindsight(data: dict[str, Any], *, db_url: str | None) -> None:
    engine = await create_hindsight_engine(db_url=db_url)
    from hindsight_api.models import RequestContext

    bank_id = str(data["bank_id"])
    contents = []
    for item in data.get("items", []):
        source_ref = str(item["source_ref"])
        contents.append(
            {
                "content": str(item["text"]),
                "context": f"source_ref:{source_ref}",
                "event_date": item.get("event_date"),
                "tags": list(item.get("tags") or []),
                "metadata": {
                    "source_path": str(item.get("source_file") or source_ref.split("#", 1)[0]),
                    "source_ref": source_ref,
                    "chunk_id": source_ref.split("#", 1)[1] if "#" in source_ref else "0",
                    "user_id": data.get("user_id", "benchmark"),
                    "artifact_type": str(item.get("artifact_type") or ""),
                    "source_type": str(item.get("source_type") or ""),
                },
                "document_id": str(item.get("document_id") or source_ref),
                "fact_type": str(item.get("fact_type") or "experience"),
            }
        )
    await engine.retain_batch_async(
        bank_id=bank_id,
        contents=contents,
        request_context=RequestContext(),
    )


async def _load_mempalace(
    data: dict[str, Any],
    *,
    palace_path: str,
    reset: bool,
) -> None:
    target = Path(palace_path)
    if reset and target.exists():
        shutil.rmtree(target, ignore_errors=True)
    engine = await create_mempalace_engine(str(target))
    bank_id = str(data["bank_id"])
    contents = []
    for item in data.get("items", []):
        source_ref = str(item["source_ref"])
        contents.append(
            {
                "content": str(item["text"]),
                "tags": list(item.get("tags") or []),
                "metadata": {
                    "source_file": str(item.get("source_file") or source_ref.split("#", 1)[0]),
                    "source_ref": source_ref,
                    "chunk_id": source_ref.split("#", 1)[1] if "#" in source_ref else "0",
                    "chunk_index": str(item.get("chunk_index") or 0),
                    "user_id": data.get("user_id", "benchmark"),
                    "artifact_type": str(item.get("artifact_type") or ""),
                    "source_type": str(item.get("source_type") or ""),
                },
                "document_id": str(item.get("document_id") or source_ref),
                "fact_type": str(item.get("fact_type") or "experience"),
            }
        )
    await engine.retain_batch_async(bank_id=bank_id, contents=contents)


async def _load_fusion(data: dict[str, Any], *, db_url: str | None, palace_path: str | None) -> None:
    from hindsight_api.models import RequestContext

    engine = await FusionMemoryEngine.create(db_url=db_url, palace_path=palace_path)
    bank_id = str(data["bank_id"])
    contents = []
    for item in data.get("items", []):
        source_ref = str(item["source_ref"])
        contents.append(
            {
                "content": str(item["text"]),
                "context": f"source_ref:{source_ref}",
                "event_date": item.get("event_date"),
                "tags": list(item.get("tags") or []),
                "metadata": {
                    "source_file": str(item.get("source_file") or source_ref.split("#", 1)[0]),
                    "source_ref": source_ref,
                    "chunk_id": source_ref.split("#", 1)[1] if "#" in source_ref else "0",
                    "chunk_index": int(item.get("chunk_index") or 0),
                    "user_id": data.get("user_id", "benchmark"),
                    "artifact_type": str(item.get("artifact_type") or ""),
                    "source_type": str(item.get("source_type") or ""),
                },
                "document_id": str(item.get("document_id") or source_ref),
                "fact_type": str(item.get("fact_type") or "experience"),
            }
        )

    await engine.retain_batch_async(
        bank_id=bank_id,
        contents=contents,
        request_context=RequestContext(),
        document_tags=["fusion"],
    )


async def main_async(args: argparse.Namespace) -> int:
    input_path = Path(args.input_json)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    palace_path = _resolve_path(args.palace_path, base_dir=input_path.parent)
    if args.palace_path:
        palace_path = _resolve_path(args.palace_path, base_dir=Path.cwd())

    target = args.target
    if target in ("both", "hindsight"):
        await _load_hindsight(data, db_url=args.db_url)
    if target in ("both", "mempalace"):
        if palace_path is None:
            raise ValueError("--palace-path required for MemPalace load")
        await _load_mempalace(data, palace_path=str(palace_path), reset=args.reset_palace)
    if target == "fusion":
        await _load_fusion(
            data,
            db_url=args.db_url,
            palace_path=str(palace_path) if palace_path else None,
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--target", choices=["both", "hindsight", "mempalace", "fusion"], default="both")
    parser.add_argument("--db-url")
    parser.add_argument("--palace-path")
    parser.add_argument("--reset-palace", action="store_true")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
