from __future__ import annotations

import types
from collections.abc import Sequence
from typing import Any

_rust_core: types.ModuleType | None
try:
    import tradeviewfusion_rust_core as _rust_core
except Exception as error:  # noqa: BLE001
    _rust_core = None
    _import_error = error
else:
    _import_error = None


def rust_core_status() -> dict[str, Any]:
    if _rust_core is None:
        return {"available": False, "module": None, "version": None, "error": str(_import_error)}
    return {
        "available": True,
        "module": "tradeviewfusion_rust_core",
        "version": getattr(_rust_core, "__version__", None),
        "error": None,
    }


def composite_sma50_slope_norm(closes: Sequence[float]) -> tuple[float, float, float] | None:
    if _rust_core is None:
        return None
    values = [float(value) for value in closes]
    if len(values) < 2:
        return None
    slope_value, slope_norm, last_sma = _rust_core.composite_sma50_slope_norm(values)
    return (float(slope_value), float(slope_norm), float(last_sma))


def calculate_heartbeat(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    sensitivity: float,
) -> float | None:
    if _rust_core is None:
        return None
    close_values = [float(value) for value in closes]
    high_values = [float(value) for value in highs]
    low_values = [float(value) for value in lows]
    if len(close_values) < 3 or len(high_values) != len(close_values) or len(low_values) != len(close_values):
        return None
    score = _rust_core.calculate_heartbeat(close_values, high_values, low_values, float(sensitivity))
    return float(score)


def portfolio_drawdown_series(equity: Sequence[float]) -> list[float] | None:
    if _rust_core is None:
        return None
    values = [float(v) for v in equity]
    if not values:
        return None
    result = _rust_core.portfolio_drawdown_series(values)
    return [float(v) for v in result]


def portfolio_rolling_sharpe(
    returns: Sequence[float],
    window: int,
    rf_daily: float = 0.0,
) -> list[float] | None:
    if _rust_core is None:
        return None
    values = [float(v) for v in returns]
    if len(values) < window:
        return None
    result = _rust_core.portfolio_rolling_sharpe(values, int(window), float(rf_daily))
    return [float(v) for v in result]


def portfolio_kelly_fraction(returns: Sequence[float]) -> float | None:
    if _rust_core is None:
        return None
    values = [float(v) for v in returns]
    if len(values) < 2:
        return None
    return float(_rust_core.portfolio_kelly_fraction(values))


def calculate_indicators_batch(
    timestamps: Sequence[int],
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    indicators: Sequence[str],
) -> dict[str, list[float]] | None:
    if _rust_core is None:
        return None
    result = _rust_core.calculate_indicators_batch(
        [int(value) for value in timestamps],
        [float(value) for value in opens],
        [float(value) for value in highs],
        [float(value) for value in lows],
        [float(value) for value in closes],
        [float(value) for value in volumes],
        [str(value) for value in indicators],
    )
    if not isinstance(result, dict):
        return None
    out: dict[str, list[float]] = {}
    for key, values in result.items():
        if isinstance(key, str) and isinstance(values, list):
            out[key] = [float(item) for item in values]
    return out
