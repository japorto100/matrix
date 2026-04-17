"""Simple Ebbinghaus-inspired decay helpers for memory metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from math import exp
from typing import Any


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def compute_retention_score(
    *,
    recall_count: int | float | str | None,
    last_recalled_at: Any,
    now: datetime | None = None,
    half_life_days: float = 14.0,
) -> float | None:
    recalled_at = _parse_datetime(last_recalled_at)
    if recalled_at is None:
        return None

    try:
        count = max(0.0, float(recall_count or 0))
    except (TypeError, ValueError):
        count = 0.0

    reference_now = now.astimezone(UTC) if now else datetime.now(UTC)
    age_days = max(0.0, (reference_now - recalled_at).total_seconds() / 86_400.0)
    reinforcement = 1.0 + min(count, 20.0) * 0.08
    decay_lambda = 0.69314718056 / max(half_life_days * reinforcement, 1.0)
    return round(exp(-decay_lambda * age_days), 4)


def derive_decay_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    enriched = dict(metadata or {})
    score = compute_retention_score(
        recall_count=enriched.get("recall_count"),
        last_recalled_at=enriched.get("last_recalled_at"),
    )
    if score is not None:
        enriched["retention_score"] = score
        if "freshness_score" not in enriched and "freshness" not in enriched:
            enriched["freshness_score"] = score
    return enriched
