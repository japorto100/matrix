"""MemPalace-backed memory adapter for the Agent runtime.

This keeps `_ref/mempalace` as the upstream source while exposing a small
Hindsight-compatible surface for our current agent code:

- `recall_async()`
- `retain_batch_async()`
- `list_memory_units()`
- `get_memory_unit()`
- `delete_memory_unit()`
- `list_banks()`

The adapter is intentionally conservative: it supports the current eval/runtime
paths without pretending MemPalace already implements Hindsight's observation /
consolidation model.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _ensure_mempalace_importable() -> None:
    root = _repo_root() / "_ref" / "mempalace"
    if not root.exists():
        raise RuntimeError(
            "MemPalace submodule missing. Run: git submodule update --init --recursive"
        )
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _hash_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _unique_strs(values: list[Any] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return out


def _decode_tags(meta: dict[str, Any]) -> list[str]:
    tags = meta.get("tags")
    if isinstance(tags, list):
        return _unique_strs(tags)
    tags_json = meta.get("tags_json")
    if isinstance(tags_json, str) and tags_json.strip():
        try:
            return _unique_strs(json.loads(tags_json))
        except json.JSONDecodeError:
            return []
    return []


def _matches_fact_type(meta: dict[str, Any], fact_type: str | list[str] | None) -> bool:
    if not fact_type:
        return True
    wanted = {fact_type} if isinstance(fact_type, str) else {str(v) for v in fact_type}
    current = str(meta.get("fact_type") or "experience")
    return current in wanted


def _matches_tags(meta: dict[str, Any], tags: list[str] | None) -> bool:
    if not tags:
        return True
    current = set(_decode_tags(meta))
    wanted = set(_unique_strs(tags))
    return wanted.issubset(current)


def _item_from_row(
    *,
    unit_id: str,
    document: str,
    meta: dict[str, Any],
    distance: float | None = None,
) -> dict[str, Any]:
    tags = _decode_tags(meta)
    return {
        "id": unit_id,
        "episode_id": unit_id,
        "text": document,
        "content": document,
        "summary": document[:280],
        "fact_type": str(meta.get("fact_type") or "experience"),
        "tags": tags,
        "entities": [],
        "metadata": {
            "user_id": meta.get("user_id"),
            "thread_id": meta.get("thread_id"),
            "agent_role": meta.get("agent_role"),
            "source_file": meta.get("source_file"),
            "source_ref": meta.get("source_ref"),
            "chunk_id": meta.get("chunk_id"),
            "document_id": meta.get("document_id"),
        },
        "event_date": meta.get("event_date"),
        "timestamp": meta.get("filed_at") or meta.get("event_date"),
        "weight": round(max(0.0, 1 - distance), 4) if distance is not None else None,
    }


@dataclass
class MemoryRecallItem:
    id: str
    text: str
    fact_type: str
    weight: float
    entities: list[str]
    tags: list[str]
    metadata: dict[str, Any]


@dataclass
class MemoryRecallResponse:
    results: list[MemoryRecallItem]
    entities: dict[str, Any] | None = None


class MempalaceMemoryEngine:
    """Thin MemPalace adapter with a Hindsight-like async API surface."""

    def __init__(self, palace_path: str):
        self.palace_path = str(Path(palace_path).expanduser())

    async def initialize(self) -> None:
        _ensure_mempalace_importable()
        from mempalace.palace import get_collection

        get_collection(self.palace_path, create=True)

    def _collection(self):
        _ensure_mempalace_importable()
        from mempalace.palace import get_collection

        return get_collection(self.palace_path, create=True)

    def _wing_for_bank(self, bank_id: str) -> str:
        return str(bank_id).strip() or "user_default"

    async def recall_async(
        self,
        *,
        bank_id: str,
        query: str,
        fact_type: str | list[str] | None = None,
        budget: Any = None,  # noqa: ARG002
        max_tokens: int | None = None,  # noqa: ARG002
        request_context: Any = None,  # noqa: ARG002
        tags: list[str] | None = None,
        include_entities: bool | None = None,  # noqa: ARG002
        max_entity_tokens: int | None = None,  # noqa: ARG002
        question_date: Any = None,  # noqa: ARG002
        **_: Any,
    ) -> MemoryRecallResponse:
        collection = self._collection()
        wing = self._wing_for_bank(bank_id)
        result = collection.query(
            query_texts=[query],
            n_results=12,
            where={"wing": wing},
            include=["documents", "metadatas", "distances"],
        )

        docs = list(result.get("documents", [[]])[0])
        metas = list(result.get("metadatas", [[]])[0])
        ids = list(result.get("ids", [[]])[0])
        distances = list(result.get("distances", [[]])[0])

        items: list[MemoryRecallItem] = []
        for unit_id, document, meta, distance in zip(ids, docs, metas, distances):
            meta = meta or {}
            if not _matches_fact_type(meta, fact_type):
                continue
            if not _matches_tags(meta, tags):
                continue
            items.append(
                MemoryRecallItem(
                    id=str(unit_id),
                    text=str(document),
                    fact_type=str(meta.get("fact_type") or "experience"),
                    weight=round(max(0.0, 1 - float(distance)), 4),
                    entities=[],
                    tags=_decode_tags(meta),
                    metadata=dict(meta),
                )
            )
        return MemoryRecallResponse(results=items, entities={})

    async def retain_batch_async(
        self,
        *,
        bank_id: str,
        contents: list[dict[str, Any]],
        request_context: Any = None,  # noqa: ARG002
        document_tags: list[str] | None = None,
        **_: Any,
    ) -> list[list[str]]:
        collection = self._collection()
        wing = self._wing_for_bank(bank_id)
        results: list[list[str]] = []

        for idx, item in enumerate(contents):
            content = str(item.get("content") or "").strip()
            if not content:
                results.append([])
                continue

            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            item_tags = _unique_strs(list(item.get("tags") or []) + list(document_tags or []))
            fact_type = str(item.get("fact_type") or "experience")
            document_id = str(
                item.get("document_id")
                or metadata.get("document_id")
                or f"{bank_id}:{idx}:{_hash_id(content)}"
            )
            room = (
                str(metadata.get("room") or "").strip()
                or str(metadata.get("agent_role") or "").strip()
                or fact_type
                or "general"
            )
            drawer_id = f"drawer_{wing}_{room}_{_hash_id(document_id)}"

            meta = {
                "wing": wing,
                "room": room,
                "bank_id": bank_id,
                "document_id": document_id,
                "source_file": str(metadata.get("source_file") or f"memory://{bank_id}/{document_id}"),
                "source_ref": str(metadata.get("source_ref") or ""),
                "chunk_index": int(metadata.get("chunk_index") or 0),
                "chunk_id": str(metadata.get("chunk_id") or metadata.get("source_ref") or "0"),
                "added_by": "matrix-agent",
                "filed_at": _now_iso(),
                "ingest_mode": "agent_memory",
                "fact_type": fact_type,
                "event_date": str(item.get("event_date") or ""),
                "user_id": metadata.get("user_id"),
                "thread_id": metadata.get("thread_id"),
                "agent_role": metadata.get("role") or metadata.get("agent_role"),
                "tags_json": json.dumps(item_tags),
            }
            meta = {key: value for key, value in meta.items() if value not in (None, "")}
            collection.upsert(documents=[content], ids=[drawer_id], metadatas=[meta])
            results.append([drawer_id])

        return results

    async def list_memory_units(
        self,
        *,
        bank_id: str,
        fact_type: str | None = None,
        search_query: str | None = None,
        limit: int = 50,
        offset: int = 0,
        request_context: Any = None,  # noqa: ARG002
        **_: Any,
    ) -> dict[str, Any]:
        collection = self._collection()
        wing = self._wing_for_bank(bank_id)

        if search_query:
            recall = await self.recall_async(
                bank_id=bank_id,
                query=search_query,
                fact_type=fact_type,
            )
            filtered = [
                _item_from_row(
                    unit_id=item.id,
                    document=item.text,
                    meta=item.metadata,
                    distance=max(0.0, 1 - item.weight),
                )
                for item in recall.results
            ]
            return {
                "items": filtered[offset : offset + limit],
                "total": len(filtered),
            }

        rows = collection.get(
            where={"wing": wing},
            include=["documents", "metadatas"],
        )
        ids = list(rows.get("ids") or [])
        docs = list(rows.get("documents") or [])
        metas = list(rows.get("metadatas") or [])

        items = []
        for unit_id, document, meta in zip(ids, docs, metas):
            meta = meta or {}
            if not _matches_fact_type(meta, fact_type):
                continue
            items.append(_item_from_row(unit_id=str(unit_id), document=str(document), meta=meta))

        items.sort(key=lambda item: str(item.get("timestamp") or ""), reverse=True)
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
        }

    async def get_memory_unit(
        self,
        *,
        unit_id: str,
        request_context: Any = None,  # noqa: ARG002
        **_: Any,
    ) -> dict[str, Any] | None:
        collection = self._collection()
        rows = collection.get(ids=[unit_id], include=["documents", "metadatas"])
        ids = list(rows.get("ids") or [])
        if not ids:
            return None
        document = str((rows.get("documents") or [""])[0])
        meta = dict((rows.get("metadatas") or [{}])[0] or {})
        return _item_from_row(unit_id=unit_id, document=document, meta=meta)

    async def delete_memory_unit(
        self,
        *,
        unit_id: str,
        request_context: Any = None,  # noqa: ARG002
        **_: Any,
    ) -> dict[str, Any]:
        collection = self._collection()
        collection.delete(ids=[unit_id])
        return {"deleted": True, "id": unit_id}

    async def list_banks(
        self,
        *,
        request_context: Any = None,  # noqa: ARG002
        **_: Any,
    ) -> list[dict[str, Any]]:
        collection = self._collection()
        rows = collection.get(include=["metadatas"])
        metas = list(rows.get("metadatas") or [])
        banks: set[str] = set()
        for meta in metas:
            bank_id = str((meta or {}).get("bank_id") or "").strip()
            if bank_id:
                banks.add(bank_id)
        return [{"bank_id": bank_id, "name": bank_id} for bank_id in sorted(banks)]

    async def list_mental_models_consolidated(
        self,
        *,
        bank_id: str,  # noqa: ARG002
        limit: int = 20,  # noqa: ARG002
        request_context: Any = None,  # noqa: ARG002
        **_: Any,
    ) -> list[dict[str, Any]]:
        return []

    async def status(self) -> dict[str, Any]:
        collection = self._collection()
        return {
            "provider": "mempalace",
            "palace_path": self.palace_path,
            "count": collection.count(),
        }
