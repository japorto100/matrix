"""Control Surface - prompt cache and request telemetry read model."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import psycopg
from fastapi import APIRouter, HTTPException, Query, Request

from agent.control.request_scope import ensure_user_scope

logger = logging.getLogger(__name__)

router = APIRouter(tags=["control", "prompt-cache"])


def _db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL", "postgresql://postgres@localhost:5433/hindsight_dev"
    )


@router.get("/prompt-cache")
async def get_prompt_cache(
    request: Request,
    user_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """Return provider-agnostic request/cache telemetry from audit replay."""

    scope = ensure_user_scope(request, user_id)
    try:
        audit_events = _query_audit_events(scope.user_id, limit=limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("prompt-cache read model failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"prompt-cache: {exc}") from exc
    read_model = build_prompt_cache_read_model(audit_events=audit_events, limit=limit)
    read_model["aggregate"] = _refresh_prompt_cache_aggregate(scope.user_id)
    return read_model


def build_prompt_cache_read_model(
    *,
    audit_events: Iterable[dict[str, Any]],
    limit: int = 100,
) -> dict[str, Any]:
    events = list(audit_events)
    items = [
        item
        for event in events
        for item in _telemetry_items_from_audit_event(event)
    ][:limit]
    by_provider = _sum_counts(items, "provider")
    by_model = _sum_counts(items, "model")
    cache_breaks = _sum_break_reasons(items)
    cache_impacts = [
        impact
        for event in events
        for impact in _cache_impacts_from_audit_event(event)
    ][:limit]
    by_thread = _thread_summaries(items, cache_impacts)
    return {
        "contract": "prompt-cache-read-model/v1",
        "items": items,
        "cache_impacts": cache_impacts,
        "summary": {
            "requests": len(items),
            "cache_impacts": len(cache_impacts),
            "cache_invalidations": sum(
                1
                for impact in cache_impacts
                if impact.get("action") == "rebind_required"
            ),
            "cache_read_tokens": sum(
                _safe_int(item["usage"].get("cache_read_tokens")) for item in items
            ),
            "cache_write_tokens": sum(
                _safe_int(item["usage"].get("cache_write_tokens")) for item in items
            ),
            "prompt_tokens": sum(_safe_int(item["usage"].get("prompt_tokens")) for item in items),
            "completion_tokens": sum(_safe_int(item["usage"].get("completion_tokens")) for item in items),
            "total_tokens": sum(_safe_int(item["usage"].get("total_tokens")) for item in items),
            "cache_breaks": sum(cache_breaks.values()),
            "unknown_cache_fields": sum(
                1
                for item in items
                for field in item["usage"].get("unknown_fields", [])
                if "cache" in str(field)
            ),
            "generated_at": _now_iso(),
        },
        "by_provider": by_provider,
        "by_model": by_model,
        "by_thread": by_thread,
        "cache_break_reasons": cache_breaks,
        "limit": limit,
    }


def build_prompt_cache_aggregate_model(
    read_model: dict[str, Any],
    *,
    user_id: str = "",
    source: str = "audit_events",
) -> dict[str, Any]:
    """Build all-time prompt-cache totals from a read model.

    This is still provider telemetry, not a local prompt-cache store. The
    aggregate is the durable Control/Ops rollup for cumulative cached-token
    counters like the ones described in Z_Prompt_Cache.md.
    """

    by_thread = _as_dict(read_model.get("by_thread"))
    summary = {
        "threads": len(by_thread),
        "requests": 0,
        "cache_impacts": 0,
        "cache_invalidations": 0,
        "cache_breaks": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "unknown_cache_fields": 0,
        "providers": [],
        "models": [],
        "generated_at": _now_iso(),
    }
    for thread in by_thread.values():
        thread_summary = _as_dict(thread)
        for key in (
            "requests",
            "cache_impacts",
            "cache_invalidations",
            "cache_breaks",
            "cache_read_tokens",
            "cache_write_tokens",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "unknown_cache_fields",
        ):
            summary[key] += _safe_int(thread_summary.get(key))
        for provider in _as_str_list(thread_summary.get("providers")):
            _append_unique(summary["providers"], provider)
        for model in _as_str_list(thread_summary.get("models")):
            _append_unique(summary["models"], model)

    summary["providers"].sort()
    summary["models"].sort()
    return {
        "contract": "prompt-cache-aggregate/v1",
        "source": source,
        "user_id": user_id,
        "summary": summary,
        "by_thread": by_thread,
    }


def _telemetry_items_from_audit_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = _as_dict(event.get("metadata"))
    raw_items: list[Any] = []
    for key in ("request_telemetry", "requestTelemetry"):
        value = metadata.get(key)
        if isinstance(value, list):
            raw_items.extend(value)
        elif value:
            raw_items.append(value)

    items: list[dict[str, Any]] = []
    for raw in raw_items:
        telemetry = _as_dict(raw)
        if not telemetry:
            continue
        usage = _as_dict(telemetry.get("usage"))
        thread_id = str(telemetry.get("thread_id") or event.get("thread_id") or "")
        prompt_digest = str(telemetry.get("prompt_digest") or "")
        tool_digest = str(telemetry.get("tool_catalog_digest") or "")
        items.append(
            {
                "event_id": f"audit:{event.get('id')}",
                "audit_ref": str(event.get("id") or ""),
                "timestamp": _iso(event.get("timestamp")),
                "thread_id": thread_id,
                "provider": str(telemetry.get("provider") or ""),
                "model": str(telemetry.get("model") or ""),
                "router": str(telemetry.get("router") or ""),
                "transport": str(telemetry.get("transport") or ""),
                "cache_retention": str(telemetry.get("cache_retention") or ""),
                "stream_strategy": str(telemetry.get("stream_strategy") or ""),
                "iteration": _safe_int(telemetry.get("iteration")),
                "prompt_digest": prompt_digest,
                "prompt_layout_digest": str(telemetry.get("prompt_layout_digest") or ""),
                "system_prompt_digest": str(telemetry.get("system_prompt_digest") or ""),
                "tool_catalog_digest": tool_digest,
                "tool_count": _safe_int(telemetry.get("tool_count")),
                "tool_names": _as_str_list(telemetry.get("tool_names")),
                "cache_break_reasons": _as_str_list(telemetry.get("cache_break_reasons")),
                "usage": usage,
                "links": {
                    "ops_event": _control_href("ops", "session", thread_id),
                    "context": _control_href("context", "thread_id", thread_id),
                },
            }
        )
    return items


def _cache_impacts_from_audit_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = _as_dict(event.get("metadata"))
    candidates: list[Any] = []
    if metadata.get("cache_impact"):
        candidates.append(metadata.get("cache_impact"))
    for key in ("runtime_events", "runtimeEvents"):
        runtime_events = metadata.get(key)
        if not isinstance(runtime_events, list):
            continue
        for runtime_event in runtime_events[:50]:
            event_metadata = _as_dict(
                runtime_event.get("metadata") if isinstance(runtime_event, dict) else None
            )
            if event_metadata.get("cache_impact"):
                candidates.append(event_metadata.get("cache_impact"))

    impacts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in candidates:
        impact = _as_dict(raw)
        if not impact:
            continue
        key = "|".join(
            (
                str(impact.get("source") or ""),
                str(impact.get("reason") or ""),
                str(impact.get("previous_digest") or ""),
                str(impact.get("next_digest") or ""),
            )
        )
        if key in seen:
            continue
        seen.add(key)
        impacts.append(
            {
                "event_id": f"audit:{event.get('id')}",
                "audit_ref": str(event.get("id") or ""),
                "timestamp": _iso(event.get("timestamp")),
                "thread_id": str(event.get("thread_id") or ""),
                "contract": str(impact.get("contract") or ""),
                "source": str(impact.get("source") or ""),
                "reason": str(impact.get("reason") or ""),
                "previous_digest": str(impact.get("previous_digest") or ""),
                "next_digest": str(impact.get("next_digest") or ""),
                "previous_digest_known": bool(impact.get("previous_digest_known")),
                "changed": bool(impact.get("changed")),
                "action": str(impact.get("action") or ""),
                "affected_sessions": impact.get("affected_sessions") or [],
                "scope": _as_dict(impact.get("scope")),
                "details": _as_dict(impact.get("details")),
                "links": {
                    "ops_event": _control_href("ops", "session", event.get("thread_id")),
                },
            }
        )
    return impacts


def _sum_counts(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(item.get(field) or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: pair[0]))


def _sum_break_reasons(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        reasons = item.get("cache_break_reasons") or []
        if not reasons:
            continue
        for reason in reasons:
            key = str(reason or "unknown")
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: pair[0]))


def _thread_summaries(
    items: list[dict[str, Any]],
    cache_impacts: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for item in items:
        thread_id = str(item.get("thread_id") or "unknown")
        usage = _as_dict(item.get("usage"))
        summary = summaries.setdefault(
            thread_id,
            {
                "thread_id": thread_id,
                "requests": 0,
                "cache_impacts": 0,
                "cache_invalidations": 0,
                "cache_breaks": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "unknown_cache_fields": 0,
                "providers": [],
                "models": [],
                "first_timestamp": "",
                "last_timestamp": "",
            },
        )
        summary["requests"] += 1
        for key in (
            "cache_read_tokens",
            "cache_write_tokens",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
        ):
            summary[key] += _safe_int(usage.get(key))
        reasons = _as_str_list(item.get("cache_break_reasons"))
        summary["cache_breaks"] += len(reasons)
        summary["unknown_cache_fields"] += sum(
            1 for field in usage.get("unknown_fields", []) if "cache" in str(field)
        )
        _append_unique(summary["providers"], item.get("provider"))
        _append_unique(summary["models"], item.get("model"))
        timestamp = str(item.get("timestamp") or "")
        if timestamp and (
            not str(summary.get("first_timestamp") or "")
            or timestamp < str(summary.get("first_timestamp") or "")
        ):
            summary["first_timestamp"] = timestamp
        if timestamp > str(summary.get("last_timestamp") or ""):
            summary["last_timestamp"] = timestamp

    for impact in cache_impacts:
        thread_id = str(impact.get("thread_id") or "unknown")
        summary = summaries.setdefault(
            thread_id,
            {
                "thread_id": thread_id,
                "requests": 0,
                "cache_impacts": 0,
                "cache_invalidations": 0,
                "cache_breaks": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "unknown_cache_fields": 0,
                "providers": [],
                "models": [],
                "first_timestamp": "",
                "last_timestamp": "",
            },
        )
        summary["cache_impacts"] += 1
        if impact.get("action") == "rebind_required":
            summary["cache_invalidations"] += 1
        timestamp = str(impact.get("timestamp") or "")
        if timestamp and (
            not str(summary.get("first_timestamp") or "")
            or timestamp < str(summary.get("first_timestamp") or "")
        ):
            summary["first_timestamp"] = timestamp
        if timestamp > str(summary.get("last_timestamp") or ""):
            summary["last_timestamp"] = timestamp

    return dict(sorted(summaries.items(), key=lambda pair: pair[0]))


def _append_unique(target: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in target:
        target.append(text)


def _query_audit_events(user_id: str, *, limit: int) -> list[dict[str, Any]]:
    with psycopg.connect(_db_url(), autocommit=True) as conn:
        cur = conn.execute(
            """
            SELECT id, timestamp, action, user_id, thread_id, metadata
            FROM agent.audit_events
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        cols = [d[0] for d in cur.description] if cur.description else []
        return [_row_to_dict(row, cols) for row in cur.fetchall()]


def _refresh_prompt_cache_aggregate(user_id: str) -> dict[str, Any]:
    """Materialize all-time per-thread prompt-cache telemetry for one user."""

    try:
        with psycopg.connect(_db_url(), autocommit=True) as conn:
            all_events = _query_all_prompt_cache_events(conn, user_id)
            read_model = build_prompt_cache_read_model(
                audit_events=all_events,
                limit=max(len(all_events) * 10, 1),
            )
            aggregate = build_prompt_cache_aggregate_model(
                read_model,
                user_id=user_id,
                source="agent.audit_events",
            )
            _write_prompt_cache_aggregate(conn, aggregate)
            return aggregate
    except Exception as exc:  # noqa: BLE001
        logger.info("prompt-cache aggregate refresh unavailable: %s", exc)
        return {
            "contract": "prompt-cache-aggregate/v1",
            "source": "unavailable",
            "user_id": user_id,
            "summary": {
                "threads": 0,
                "requests": 0,
                "cache_impacts": 0,
                "cache_invalidations": 0,
                "cache_breaks": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "unknown_cache_fields": 0,
                "providers": [],
                "models": [],
                "generated_at": _now_iso(),
            },
            "by_thread": {},
        }


def _query_all_prompt_cache_events(conn: Any, user_id: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT id, timestamp, action, user_id, thread_id, metadata
        FROM agent.audit_events
        WHERE user_id = %s
          AND metadata IS NOT NULL
        ORDER BY timestamp ASC
        """,
        (user_id,),
    )
    cols = [d[0] for d in cur.description] if cur.description else []
    return [_row_to_dict(row, cols) for row in cur.fetchall()]


def _write_prompt_cache_aggregate(conn: Any, aggregate: dict[str, Any]) -> None:
    user_id = str(aggregate.get("user_id") or "")
    by_thread = _as_dict(aggregate.get("by_thread"))
    if not user_id:
        return

    conn.execute(
        "DELETE FROM agent.prompt_cache_thread_summaries WHERE user_id = %s",
        (user_id,),
    )
    for thread_id, raw_summary in by_thread.items():
        summary = _as_dict(raw_summary)
        conn.execute(
            """
            INSERT INTO agent.prompt_cache_thread_summaries (
                user_id, thread_id, first_seen, last_seen, request_count,
                cache_impact_count, cache_invalidation_count, cache_break_count,
                cache_read_tokens, cache_write_tokens, prompt_tokens,
                completion_tokens, total_tokens, unknown_cache_fields,
                providers, models, thread_summary, updated_at
            )
            VALUES (
                %s, %s, NULLIF(%s, '')::timestamptz, NULLIF(%s, '')::timestamptz,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s::jsonb, %s::jsonb, %s::jsonb, now()
            )
            ON CONFLICT (user_id, thread_id) DO UPDATE SET
                last_seen = EXCLUDED.last_seen,
                request_count = EXCLUDED.request_count,
                cache_impact_count = EXCLUDED.cache_impact_count,
                cache_invalidation_count = EXCLUDED.cache_invalidation_count,
                cache_break_count = EXCLUDED.cache_break_count,
                cache_read_tokens = EXCLUDED.cache_read_tokens,
                cache_write_tokens = EXCLUDED.cache_write_tokens,
                prompt_tokens = EXCLUDED.prompt_tokens,
                completion_tokens = EXCLUDED.completion_tokens,
                total_tokens = EXCLUDED.total_tokens,
                unknown_cache_fields = EXCLUDED.unknown_cache_fields,
                providers = EXCLUDED.providers,
                models = EXCLUDED.models,
                thread_summary = EXCLUDED.thread_summary,
                updated_at = now()
            """,
            (
                user_id,
                str(thread_id),
                str(summary.get("first_timestamp") or ""),
                str(summary.get("last_timestamp") or ""),
                _safe_int(summary.get("requests")),
                _safe_int(summary.get("cache_impacts")),
                _safe_int(summary.get("cache_invalidations")),
                _safe_int(summary.get("cache_breaks")),
                _safe_int(summary.get("cache_read_tokens")),
                _safe_int(summary.get("cache_write_tokens")),
                _safe_int(summary.get("prompt_tokens")),
                _safe_int(summary.get("completion_tokens")),
                _safe_int(summary.get("total_tokens")),
                _safe_int(summary.get("unknown_cache_fields")),
                json.dumps(_as_str_list(summary.get("providers"))),
                json.dumps(_as_str_list(summary.get("models"))),
                json.dumps(summary, default=str),
            ),
        )


def _row_to_dict(row: Any, cols: list[str]) -> dict[str, Any]:
    data = dict(zip(cols, row, strict=True))
    data["metadata"] = _as_dict(data.get("metadata"))
    if data.get("timestamp"):
        data["timestamp"] = _iso(data["timestamp"])
    return data


def _control_href(tab: str, query_key: str, query_value: Any) -> str:
    value = str(query_value or "").strip()
    if not value:
        return f"/control/{tab}"
    return f"/control/{tab}?{query_key}={quote(value)}"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list | tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _iso(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value or _now_iso())


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
