"""Control Surface — Episodes / Memory Units (Slice 3 backend).

Reads DIRECTLY from Hindsight (hindsight_api.MemoryEngine), NOT from the
legacy memory_engine/episodic_store.py SQLite store.

Supports faceted filters (fact_type, search), pagination, single get, delete, patch.
Hindsight's native API supports: bank_id, fact_type, search_query, limit, offset.
Additional filters (role, session, date, tags, confidence) are applied client-side
in-memory after fetch — acceptable for Phase 1 (< 1000 episodes), Phase 2 would push
these into Hindsight's API extension or a raw SQL bypass.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from agent.control.request_scope import resolve_scope
from agent.memory.engine import get_bank_id, get_memory_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "episodes"])


def _apply_post_filters(
    items: list[dict[str, Any]],
    *,
    role: str | None,
    session_id: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
    tags: list[str] | None,
    confidence_min: float | None,
) -> list[dict[str, Any]]:
    """Client-side filter for facets not supported by Hindsight native API."""
    out = items
    if role:
        out = [
            i
            for i in out
            if (i.get("metadata") or {}).get("agent_role") == role
            or (i.get("tags") or [])
            and role in (i.get("tags") or [])
        ]
    if session_id:
        out = [
            i for i in out if (i.get("metadata") or {}).get("session_id") == session_id
        ]
    if from_date is not None:
        out = [
            i
            for i in out
            if i.get("event_date")
            and datetime.fromisoformat(str(i["event_date"]).replace("Z", "+00:00"))
            >= from_date
        ]
    if to_date is not None:
        out = [
            i
            for i in out
            if i.get("event_date")
            and datetime.fromisoformat(str(i["event_date"]).replace("Z", "+00:00"))
            <= to_date
        ]
    if tags:
        tag_set = set(tags)
        out = [i for i in out if tag_set.issubset(set(i.get("tags") or []))]
    if confidence_min is not None:
        out = [
            i
            for i in out
            if float((i.get("metadata") or {}).get("confidence", 1.0)) >= confidence_min
        ]
    return out


@router.get("/episodes")
async def list_episodes(
    request: Request,
    user_id: str | None = None,
    role: str | None = None,
    session_id: str | None = None,
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    tags: list[str] | None = Query(None),
    confidence_min: float | None = None,
    fact_type: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Faceted query over memory_units via Hindsight.

    - `fact_type` (world/experience/opinion), `search`, `limit`, `offset` are
      passed directly to Hindsight.
    - `role`, `session_id`, `from_date`, `to_date`, `tags`, `confidence_min`
      are applied in-memory after fetch (acceptable for Phase 1 dev).
    """
    engine = await get_memory_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Memory engine disabled")

    scope = resolve_scope(request, requested_user_id=user_id)
    bank_id = get_bank_id(scope.user_id)

    try:
        from hindsight_api.models import RequestContext

        # Fetch more than limit if we're going to filter client-side
        has_client_filters = any(
            [role, session_id, from_date, to_date, tags, confidence_min]
        )
        fetch_limit = limit * 4 if has_client_filters else limit

        result = await engine.list_memory_units(
            bank_id=bank_id,
            fact_type=fact_type,
            search_query=search,
            limit=fetch_limit,
            offset=offset,
            request_context=RequestContext(),
        )
        items = result.get("items", [])

        if has_client_filters:
            items = _apply_post_filters(
                items,
                role=role,
                session_id=session_id,
                from_date=from_date,
                to_date=to_date,
                tags=tags,
                confidence_min=confidence_min,
            )
            items = items[:limit]

        return {
            "items": items,
            "total": result.get("total", len(items)),
            "limit": limit,
            "offset": offset,
            "bank_id": bank_id,
            "user_id": scope.user_id,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("list_episodes failed")
        raise HTTPException(status_code=500, detail=f"list_episodes: {e}") from e


@router.get("/episodes/{episode_id}")
async def get_episode(
    episode_id: str,
    request: Request,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Fetch single episode by id via Hindsight get_memory_unit."""
    engine = await get_memory_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Memory engine disabled")

    scope = resolve_scope(request, requested_user_id=user_id)

    try:
        from hindsight_api.models import RequestContext

        result = await engine.get_memory_unit(  # type: ignore[call-arg]  # Hindsight API version mismatch
            unit_id=episode_id,
            request_context=RequestContext(),
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Episode not found")
        unit_user = (
            (result.get("metadata") or {}).get("user_id")
            if isinstance(result, dict)
            else None
        )
        if unit_user and unit_user != scope.user_id:
            raise HTTPException(status_code=404, detail="Episode not found")
        return result
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("get_episode failed")
        raise HTTPException(status_code=500, detail=f"get_episode: {e}") from e


@router.delete("/episodes/{episode_id}")
async def delete_episode(
    episode_id: str,
    request: Request,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Delete single episode (approval-write, 30s token expected in header).

    D22: vollstaendig inkl. writes — approval-gating done by middleware (exec-12).
    """
    engine = await get_memory_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Memory engine disabled")

    scope = resolve_scope(request, requested_user_id=user_id)

    try:
        from hindsight_api.models import RequestContext

        current = await engine.get_memory_unit(  # type: ignore[call-arg]  # Hindsight API version mismatch
            unit_id=episode_id,
            request_context=RequestContext(),
        )
        if current is None:
            raise HTTPException(status_code=404, detail="Episode not found")
        current_user = (current.get("metadata") or {}).get("user_id")
        if current_user and current_user != scope.user_id:
            raise HTTPException(status_code=404, detail="Episode not found")

        result = await engine.delete_memory_unit(
            unit_id=episode_id,
            request_context=RequestContext(),
        )
        return {"status": "deleted", "episode_id": episode_id, "result": result}
    except Exception as e:  # noqa: BLE001
        logger.exception("delete_episode failed")
        raise HTTPException(status_code=500, detail=f"delete_episode: {e}") from e
