"""Shared fixtures for indicator_engine tests.

generate_test_ohlcv() based on Kaabar 2026, Ch. 2 — guarantees realistic
OHLC constraints: high >= max(open, close), low <= min(open, close),
open[i] ≈ close[i-1].
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _generate_ohlcv(
    length: int = 1000,
    *,
    seed: int | None = 42,
    with_volume: bool = True,
    start_price: float = 150.0,
) -> pd.DataFrame:
    """Return a DataFrame with columns open/high/low/close(/volume).

    Constraints (Kaabar Ch. 2):
      - high >= max(open, close)
      - low  <= min(open, close)
      - open[i] ≈ close[i-1] + small noise  (gap ≤ ±3)

    Parameters
    ----------
    length : int
        Number of bars.
    seed : int | None
        RNG seed for reproducibility. ``None`` for random.
    with_volume : bool
        If True, adds a realistic volume column.
    start_price : float
        Opening price of the first bar.
    """
    rng = np.random.default_rng(seed)

    open_ = np.empty(length)
    high = np.empty(length)
    low = np.empty(length)
    close = np.empty(length)

    # First bar
    open_[0] = start_price
    close[0] = open_[0] + rng.uniform(-5, 5)
    high[0] = max(open_[0], close[0]) + rng.uniform(0, 5)
    low[0] = min(open_[0], close[0]) - rng.uniform(0, 5)

    for i in range(1, length):
        open_[i] = close[i - 1] + rng.uniform(-3, 3)
        close[i] = open_[i] + rng.uniform(-5, 5)
        high[i] = max(open_[i], close[i]) + rng.uniform(0, 5)
        low[i] = min(open_[i], close[i]) - rng.uniform(0, 5)

    data: dict[str, np.ndarray] = {
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    }

    if with_volume:
        # Realistic volume: base + volatility-proportional component
        bar_range = high - low
        base_vol = rng.integers(500_000, 2_000_000, size=length).astype(float)
        data["volume"] = base_vol + (bar_range / bar_range.mean()) * 500_000

    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def ohlcv_1000() -> pd.DataFrame:
    """1000-bar OHLCV DataFrame (seed=42, deterministic)."""
    return _generate_ohlcv(1000, seed=42)


@pytest.fixture()
def ohlcv_500() -> pd.DataFrame:
    """500-bar OHLCV DataFrame (seed=42, deterministic)."""
    return _generate_ohlcv(500, seed=42)


@pytest.fixture()
def ohlcv_100() -> pd.DataFrame:
    """100-bar short DataFrame for edge-case / warmup tests."""
    return _generate_ohlcv(100, seed=42)


@pytest.fixture()
def closes_1000(ohlcv_1000: pd.DataFrame) -> list[float]:
    """Plain list of 1000 close prices."""
    return ohlcv_1000["close"].tolist()


@pytest.fixture()
def ohlcv_dict_1000(ohlcv_1000: pd.DataFrame) -> dict[str, list[float]]:
    """OHLCV as dict of lists — matches indicator_engine input format."""
    return {
        "open": ohlcv_1000["open"].tolist(),
        "high": ohlcv_1000["high"].tolist(),
        "low": ohlcv_1000["low"].tolist(),
        "close": ohlcv_1000["close"].tolist(),
        "volume": ohlcv_1000["volume"].tolist(),
    }


@pytest.fixture()
def ohlcv_points_1000(ohlcv_1000: pd.DataFrame) -> list:
    """list[OHLCVPoint] from 1000-bar DataFrame — for endpoint handlers."""
    from indicator_engine.models import OHLCVPoint

    return [
        OHLCVPoint(
            time=i,
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
        )
        for i, row in ohlcv_1000.iterrows()
    ]


@pytest.fixture()
def ohlcv_points_100(ohlcv_100: pd.DataFrame) -> list:
    """list[OHLCVPoint] from 100-bar DataFrame — short edge-case tests."""
    from indicator_engine.models import OHLCVPoint

    return [
        OHLCVPoint(
            time=i,
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
        )
        for i, row in ohlcv_100.iterrows()
    ]
