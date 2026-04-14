"""Smoke test: verify conftest fixtures produce valid OHLCV data."""

from __future__ import annotations

import pandas as pd


def test_ohlcv_1000_shape(ohlcv_1000: pd.DataFrame) -> None:
    assert ohlcv_1000.shape == (1000, 5)
    assert list(ohlcv_1000.columns) == ["open", "high", "low", "close", "volume"]


def test_ohlcv_constraints(ohlcv_1000: pd.DataFrame) -> None:
    """Kaabar Ch.2 invariants: high >= max(O,C), low <= min(O,C)."""
    df = ohlcv_1000
    oc_max = df[["open", "close"]].max(axis=1)
    oc_min = df[["open", "close"]].min(axis=1)
    assert (df["high"] >= oc_max).all(), "high must be >= max(open, close)"
    assert (df["low"] <= oc_min).all(), "low must be <= min(open, close)"


def test_ohlcv_deterministic(ohlcv_1000: pd.DataFrame) -> None:
    """Same seed → same data across runs."""
    from tests.conftest import _generate_ohlcv

    df2 = _generate_ohlcv(1000, seed=42)
    pd.testing.assert_frame_equal(ohlcv_1000, df2)


def test_ohlcv_gap_continuity(ohlcv_1000: pd.DataFrame) -> None:
    """open[i] should be close to close[i-1] (gap <= 3)."""
    df = ohlcv_1000
    gaps = (df["open"].iloc[1:].values - df["close"].iloc[:-1].values)
    assert abs(gaps).max() <= 3.0, f"Max gap {abs(gaps).max():.2f} exceeds 3.0"


def test_volume_positive(ohlcv_1000: pd.DataFrame) -> None:
    assert (ohlcv_1000["volume"] > 0).all()


def test_ohlcv_100_short(ohlcv_100: pd.DataFrame) -> None:
    assert ohlcv_100.shape == (100, 5)


def test_closes_list(closes_1000: list[float]) -> None:
    assert len(closes_1000) == 1000
    assert all(isinstance(v, float) for v in closes_1000)


def test_ohlcv_dict(ohlcv_dict_1000: dict[str, list[float]]) -> None:
    assert set(ohlcv_dict_1000.keys()) == {"open", "high", "low", "close", "volume"}
    assert all(len(v) == 1000 for v in ohlcv_dict_1000.values())
