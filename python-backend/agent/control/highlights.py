"""Control Surface — Memory Highlights (Slice 3 backend).

Builds lightweight highlights from recent episodes for the MemoryPage card.
This replaces frontend-only MOCK_HIGHLIGHTS with a real API endpoint.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Request

from agent.control.request_scope import effective_user_id
from memory_fusion.engine import get_bank_id, get_memory_engine

router = APIRouter(tags=["control", "highlights"])


def _to_item(unit: dict[str, Any], idx: int) -> dict[str, Any]:
    text = (
        unit.get("summary")
        or unit.get("content")
        or unit.get("input")
        or unit.get("output")
        or ""
    )
    text = str(text).strip()
    if len(text) > 220:
        text = f"{text[:217]}..."

    tags = unit.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tags = [str(t).strip() for t in tags if str(t).strip()]

    title = (tags[0] if tags else unit.get("agent_role") or f"Highlight {idx}").replace(
        "_", " "
    )
    title = title.title()

    if "\n" in text:
        fmt = "bullets"
    elif len(text) <= 110:
        fmt = "one_liner"
    else:
        fmt = "paragraph"

    source_id = unit.get("episode_id") or unit.get("id") or f"h_{idx}"
    return {
        "id": f"hl_{idx}",
        "title": title,
        "content": text or "No text content found in episode.",
        "format": fmt,
        "query": " ".join(tags[:2]) if tags else title,
        "source_episode_ids": [str(source_id)],
    }


@router.get("/memory/highlights")
async def get_memory_highlights(
    request: Request,
    user_id: str = "local",
    limit: int = 3,
) -> dict[str, Any]:
    """Return top memory highlights derived from recent episodic units."""
    engine = await get_memory_engine()
    if engine is None:
        return {"items": [], "total": 0}

    scoped_user_id = effective_user_id(request, user_id)
    bank_id = get_bank_id(scoped_user_id)
    req_limit = max(1, min(limit * 6, 60))

    try:
        from hindsight_api.models import RequestContext

        req_ctx = RequestContext()
        result = await engine.list_memory_units(
            bank_id=bank_id,
            limit=req_limit,
            offset=0,
            request_context=req_ctx,
        )
    except Exception:
        return {"items": [], "total": 0}

    raw_items = result.get("items") if isinstance(result, dict) else []
    if not isinstance(raw_items, list):
        raw_items = []

    # Prefer more frequent tags first to surface recurring themes.
    tag_counts: Counter[str] = Counter()
    for unit in raw_items:
        tags = unit.get("tags") if isinstance(unit, dict) else None
        if isinstance(tags, str):
            tag_counts.update([tags])
        elif isinstance(tags, list):
            tag_counts.update([str(t) for t in tags if str(t).strip()])

    def sort_key(unit: dict[str, Any]) -> tuple[int, int]:
        tags = unit.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        score = sum(tag_counts.get(str(t), 0) for t in tags)
        ts = unit.get("timestamp") or unit.get("created_at") or ""
        return (score, 1 if ts else 0)

    ranked = sorted(
        [u for u in raw_items if isinstance(u, dict)],
        key=sort_key,
        reverse=True,
    )

    items = [
        _to_item(unit, idx + 1) for idx, unit in enumerate(ranked[: max(1, limit)])
    ]
    return {"items": items, "total": len(items)}
