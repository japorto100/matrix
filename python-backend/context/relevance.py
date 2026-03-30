# Relevance Scoring — 4 Dimensionen (CE Sek. 4)
# Phase 10b.1

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

WEIGHT_FRESHNESS = 0.30
WEIGHT_PROXIMITY = 0.25
WEIGHT_CONFIDENCE = 0.25
WEIGHT_REGIME_FIT = 0.20

MIN_RELEVANCE = 0.3


def compute_freshness(timestamp_str: str | None, max_age_hours: float = 168) -> float:
    """Freshness 0-1. Events < 2h = 1.0, < 24h = 0.7, < 7d = 0.3."""
    if not timestamp_str:
        return 0.5
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_hours = (now - ts).total_seconds() / 3600
        if age_hours < 2:
            return 1.0
        if age_hours < 24:
            return 0.7
        if age_hours < 168:
            return 0.3
        return max(0.1, 1.0 - (age_hours / max_age_hours))
    except Exception:
        return 0.5


def compute_user_proximity(
    fragment_symbols: list[str],
    user_kg: dict[str, Any] | None,
) -> float:
    """User-Proximity: hat_position=1.0, watchlist=0.7, kein_bezug=0.2."""
    if not user_kg or not fragment_symbols:
        return 0.5
    positions = set(user_kg.get("positions", []) or [])
    watchlist = set(user_kg.get("watchlist", []) or [])
    for s in fragment_symbols:
        if s in positions:
            return 1.0
        if s in watchlist:
            return 0.7
    return 0.2


def compute_regime_fit(
    fragment_symbols: list[str],
    current_regime: str | None,
) -> float:
    """Regime-Fit placeholder."""
    if not current_regime:
        return 0.6
    return 0.6


def relevance_score(
    fragment: dict[str, Any],
    query: str,
    *,
    user_kg: dict[str, Any] | None = None,
    current_regime: str | None = None,
) -> float:
    """Composite relevance score (4 dimensions). CE Sek. 4.2."""
    freshness = compute_freshness(fragment.get("timestamp"))
    symbols = fragment.get("symbols", []) or fragment.get("metadata", {}).get("symbols", [])
    proximity = compute_user_proximity(symbols, user_kg)
    confidence = float(fragment.get("confidence", fragment.get("metadata", {}).get("confidence", 0.7)))
    regime_fit = compute_regime_fit(symbols, current_regime)

    score = (
        WEIGHT_FRESHNESS * freshness
        + WEIGHT_PROXIMITY * proximity
        + WEIGHT_CONFIDENCE * confidence
        + WEIGHT_REGIME_FIT * regime_fit
    )
    return max(0.0, min(1.0, score))
