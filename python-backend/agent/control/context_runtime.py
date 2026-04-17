"""Shared runtime/control helpers for memory and context inspector payloads."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from context.policy import apply_context_policy, build_degradation_flags
from memory_fusion.decay import derive_decay_metadata
from memory_fusion.semantics import (
    enrich_metadata_with_semantics,
)

logger = logging.getLogger(__name__)


def db_url() -> str:
    return os.environ.get(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres@localhost:5433/hindsight_dev",
    )


def normalize_health(status: str | None) -> str:
    value = str(status or "").strip().lower()
    if value in {"ok", "ready", "healthy", "online"}:
        return "healthy"
    if value in {"warning", "degraded"}:
        return "degraded"
    if value in {"offline", "error", "unavailable"}:
        return "offline"
    return "unknown"


def to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, (int, float)):
        # Session timestamps are stored in milliseconds.
        ts = float(value)
        if ts > 10_000_000_000:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=UTC).isoformat()
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return to_iso(int(text))
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC).isoformat()
    except ValueError:
        return text


def coerce_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def approx_tokens(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped.split()))


def latest_session_for_user(user_id: str) -> dict[str, Any] | None:
    try:
        with psycopg.connect(db_url(), autocommit=True, connect_timeout=2) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                row = cur.execute(
                    """
                    SELECT session_id, session_type, user_id, thread_id, bank_id, status,
                           metadata, summary, runs, started_at, completed_at,
                           created_at, updated_at
                    FROM agent.sessions
                    WHERE session_type = 'agent_chat'
                      AND user_id = %s
                    ORDER BY COALESCE(updated_at, created_at) DESC
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
                return dict(row) if row else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("latest_session_for_user failed: %s", exc)
        return None


def _pick_text(item: dict[str, Any]) -> str:
    for field in ("text", "summary", "content", "input", "output"):
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _title_for_item(item: dict[str, Any], metadata: dict[str, Any]) -> str:
    for value in (
        metadata.get("artifact_type"),
        item.get("fact_type"),
        metadata.get("source_type"),
        "memory item",
    ):
        text = str(value or "").strip()
        if text:
            return text.replace("_", " ").title()
    return "Memory Item"


def build_context_blocks(items: list[dict[str, Any]], *, limit: int = 8) -> tuple[list[dict[str, Any]], dict[str, int]]:
    blocks: list[dict[str, Any]] = []

    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        raw_metadata = dict(item.get("metadata") or item.get("document_metadata") or {})
        metadata = enrich_metadata_with_semantics(
            derive_decay_metadata(raw_metadata),
            fact_type=str(item.get("fact_type") or raw_metadata.get("fact_type") or ""),
        )
        text = _pick_text(item)
        blocks.append(
            {
                "id": str(item.get("id") or item.get("memory_unit_id") or item.get("document_id") or len(blocks)),
                "title": _title_for_item(item, metadata),
                "preview": text[:240] + ("..." if len(text) > 240 else ""),
                "sourceLayer": str(metadata.get("memory_layer") or "unknown"),
                "sourceType": str(metadata.get("source_type") or "unknown"),
                "artifactType": str(metadata.get("artifact_type") or "unknown"),
                "groundingStatus": str(metadata.get("grounding_status") or "unknown"),
                "promotionStatus": str(metadata.get("promotion_status") or "not_applicable"),
                "provenanceRef": str(
                    metadata.get("provenance_ref")
                    or metadata.get("source_ref")
                    or metadata.get("document_id")
                    or metadata.get("chunk_id")
                    or ""
                ),
                "sourceConfidence": metadata.get("source_confidence"),
                "actorRole": str(metadata.get("actor_role") or "unknown"),
                "status": str(metadata.get("status") or "available"),
                "freshness": metadata.get("freshness_score") or metadata.get("freshness"),
                "supportCount": metadata.get("support_count"),
                "conflictCount": metadata.get("conflict_count"),
                "factType": str(item.get("fact_type") or metadata.get("fact_type") or ""),
                "route": str(item.get("fusion_route") or metadata.get("fusion_route") or ""),
                "tokenCount": approx_tokens(text),
            }
        )

    ordered, counts, _ = apply_context_policy(blocks, consumer="frontend_ui", limit=limit)
    return ordered, counts


async def load_memory_items(engine: Any, *, bank_id: str, limit: int = 12) -> list[dict[str, Any]]:
    if engine is None:
        return []
    try:
        from hindsight_api.models import RequestContext

        result = await engine.list_memory_units(
            bank_id=bank_id,
            limit=limit,
            offset=0,
            request_context=RequestContext(),
            consumer="frontend_ui",
        )
        items = result.get("items") if isinstance(result, dict) else []
        return items if isinstance(items, list) else []
    except Exception as exc:  # noqa: BLE001
        logger.debug("load_memory_items failed for bank %s: %s", bank_id, exc)
        return []


async def build_runtime_inspector(
    *,
    engine: Any,
    user_id: str,
    bank_id: str,
    provider: str,
    kg_node_count: int | None = None,
) -> dict[str, Any]:
    session = latest_session_for_user(user_id)
    summary = coerce_dict(session.get("summary")) if session else {}
    metadata = coerce_dict(session.get("metadata")) if session else {}
    latest_run = coerce_dict(metadata.get("latest_run") or metadata.get("latestRun"))

    live_items = await load_memory_items(engine, bank_id=bank_id)
    live_blocks, live_counts = build_context_blocks(live_items)

    stored_counts = coerce_dict(latest_run.get("sourceLayerCounts"))
    source_layer_counts = {
        key: int(value)
        for key, value in (stored_counts or live_counts).items()
        if isinstance(value, (int, float, str)) and str(value).strip()
    }
    context_blocks = latest_run.get("contextBlocks")
    if not isinstance(context_blocks, list) or not context_blocks:
        context_blocks = live_blocks
    else:
        context_blocks, source_layer_counts, _ = apply_context_policy(
            [dict(block or {}) for block in context_blocks],
            consumer="frontend_ui",
            kg_node_count=kg_node_count,
        )

    degradation_flags = latest_run.get("degradationFlags")
    if not isinstance(degradation_flags, list):
        degradation_flags = build_degradation_flags(
            source_layer_counts=source_layer_counts,
            context_blocks=context_blocks,
            kg_node_count=kg_node_count,
        )
    query_gate = coerce_dict(latest_run.get("queryGate"))

    active_session = {
        "sessionId": session.get("session_id") if session else None,
        "threadId": session.get("thread_id") if session else None,
        "status": session.get("status") if session else None,
        "startedAt": to_iso(session.get("started_at")) if session else None,
        "completedAt": to_iso(session.get("completed_at")) if session else None,
        "updatedAt": to_iso(session.get("updated_at")) if session else None,
        "provider": latest_run.get("provider") or summary.get("provider") or provider,
        "model": latest_run.get("model") or summary.get("model"),
        "promptTokens": int(
            latest_run.get("promptTokens")
            or summary.get("promptTokens")
            or summary.get("prompt_tokens")
            or 0
        ),
        "completionTokens": int(
            latest_run.get("completionTokens")
            or summary.get("completionTokens")
            or summary.get("completion_tokens")
            or 0
        ),
        "reasoningTokens": int(
            latest_run.get("reasoningTokens")
            or summary.get("reasoningTokens")
            or summary.get("reasoning_tokens")
            or 0
        ),
        "cachedTokens": int(
            latest_run.get("cachedTokens")
            or summary.get("cachedTokens")
            or summary.get("cached_tokens")
            or 0
        ),
        "totalTokens": int(
            latest_run.get("totalTokens")
            or summary.get("totalTokens")
            or summary.get("total_tokens")
            or 0
        ),
        "contextPressure": latest_run.get("contextPressure") or summary.get("contextPressure") or 0,
    }

    return {
        "memoryProvider": provider,
        "activeSession": active_session,
        "sourceLayerCounts": source_layer_counts,
        "contextBlocks": context_blocks,
        "degradationFlags": degradation_flags,
        "queryGate": query_gate,
        "hasPersistedRunMetadata": bool(latest_run),
        "liveContextBlockCount": len(live_blocks),
    }
