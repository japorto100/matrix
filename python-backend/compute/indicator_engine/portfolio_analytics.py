"""Portfolio analytics: correlations, rolling metrics, drawdown analysis.

Phase 5b — called via Go proxy → /api/v1/portfolio/*.
All computation uses numpy/scipy/pandas; no external API calls.
"""
from __future__ import annotations

import asyncio
from typing import Literal, cast

import httpx
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from shared.config import GO_GATEWAY_URL

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AssetOHLCV(BaseModel):
    symbol: str
    close: list[float]
    timestamps: list[str] = Field(default_factory=list)


class CorrelationRequest(BaseModel):
    symbols: list[str]
    timeframe: str = "1D"
    limit: int = 300
    method: Literal["pearson", "spearman", "kendall"] = "pearson"


class CorrelationResponse(BaseModel):
    correlation_matrix: dict[str, dict[str, float]]
    diversification_score: float
    cluster_groups: list[list[str]]


async def fetch_ohlcv_from_go(symbol: str, timeframe: str, limit: int) -> AssetOHLCV | None:
    url = f"{GO_GATEWAY_URL}/api/v1/ohlcv"
    params = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success") or not data.get("data"):
                return None
            
            closes = [c["close"] for c in data["data"]]
            timestamps = [str(c["time"]) for c in data["data"]]
            return AssetOHLCV(symbol=symbol, close=closes, timestamps=timestamps)
        except Exception as e:
            print(f"Error fetching OHLCV for {symbol} from Go Gateway: {e}")
            return None


class AssetFullOHLCV(BaseModel):
    symbol: str
    close: list[float]
    high: list[float]
    low: list[float]
    volume: list[float]
    timestamps: list[str] = Field(default_factory=list)


async def fetch_full_ohlcv_from_go(symbol: str, timeframe: str, limit: int) -> AssetFullOHLCV | None:
    url = f"{GO_GATEWAY_URL}/api/v1/ohlcv"
    params = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success") or not data.get("data"):
                return None
            candles = data["data"]
            closes = [c.get("close", 0.0) for c in candles]
            highs = [c.get("high", c.get("close", 0.0)) for c in candles]
            lows = [c.get("low", c.get("close", 0.0)) for c in candles]
            volumes = [c.get("volume", 1.0) for c in candles]
            timestamps = [str(c["time"]) for c in candles]
            return AssetFullOHLCV(
                symbol=symbol,
                close=closes,
                high=highs,
                low=lows,
                volume=volumes,
                timestamps=timestamps,
            )
        except Exception as e:
            print(f"Error fetching full OHLCV for {symbol} from Go Gateway: {e}")
            return None


class EquityPoint(BaseModel):
    time: str
    equity: float


class RollingMetricsRequest(BaseModel):
    equity_curve: list[EquityPoint]
    window_days: int = 20
    risk_free_rate: float = 0.04  # annualised


class RollingMetricsPoint(BaseModel):
    time: str
    sharpe: float | None
    sortino: float | None
    calmar: float | None


class RollingMetricsResponse(BaseModel):
    points: list[RollingMetricsPoint]
    summary: dict[str, float]


class DrawdownRequest(BaseModel):
    equity_curve: list[EquityPoint]


class DrawdownPeriod(BaseModel):
    start: str
    trough: str
    end: str | None
    depth: float        # negative fraction, e.g. -0.12 = -12 %
    duration_days: int
    recovery_days: int | None


class DrawdownResponse(BaseModel):
    max_drawdown: float
    avg_drawdown: float
    periods: list[DrawdownPeriod]
    underwater_curve: list[dict[str, str | float]]  # [{time: str, drawdown: float}]


class OptimizeRequest(BaseModel):
    symbols: list[str]
    method: Literal["equal_weight", "min_variance", "inverse_vol", "hrp"] = "equal_weight"
    timeframe: str = "1D"
    limit: int = 252  # 1 year of daily data


class OptimizeResponse(BaseModel):
    weights: dict[str, float]
    method: str
    expected_volatility: float | None = None
    dendrogram_order: list[str] | None = None


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------

def _group_by_cluster(symbols: list[str], labels: list[int]) -> list[list[str]]:
    groups: dict[int, list[str]] = {}
    for sym, lab in zip(symbols, labels):
        groups.setdefault(lab, []).append(sym)
    return list(groups.values())


async def compute_correlations(req: CorrelationRequest) -> CorrelationResponse:
    if len(req.symbols) < 2:
        # Return trivial identity matrix for single asset
        sym = req.symbols[0] if req.symbols else "unknown"
        return CorrelationResponse(
            correlation_matrix={sym: {sym: 1.0}},
            diversification_score=0.0,
            cluster_groups=[[sym]],
        )

    # Fetch OHLCV concurrently for all symbols
    tasks = [fetch_ohlcv_from_go(sym, req.timeframe, req.limit) for sym in req.symbols]
    fetched_assets = await asyncio.gather(*tasks)
    assets = [a for a in fetched_assets if a is not None and len(a.close) > 10]

    if len(assets) < 2:
        return CorrelationResponse(
            correlation_matrix={},
            diversification_score=0.0,
            cluster_groups=[],
        )

    # Build log-returns DataFrame
    min_len = min(len(a.close) for a in assets)
    data = {
        a.symbol: np.log(
            np.array(a.close[-min_len:]) / np.roll(np.array(a.close[-min_len:]), 1)
        )[1:]
        for a in assets
    }
    returns = pd.DataFrame(data)
    corr = returns.corr(method=req.method)  # type: ignore[arg-type]

    # Diversification score = 1 - mean |off-diagonal correlation|
    n = len(corr)
    if n > 1:
        upper = corr.values[np.triu_indices(n, k=1)]
        div_score = float(1.0 - np.mean(np.abs(upper)))
    else:
        div_score = 0.0

    # Hierarchical clustering for grouping
    try:
        from scipy.cluster.hierarchy import fcluster, linkage
        from scipy.spatial.distance import squareform

        dist = squareform(np.clip(0.5 * (1 - corr.values), 0, None))
        link = linkage(dist, method="single")
        labels = fcluster(link, t=0.5, criterion="distance").tolist()
        groups = _group_by_cluster(list(corr.columns), labels)
    except Exception:  # noqa: BLE001
        groups = [list(corr.columns)]

    correlation_matrix = cast(dict[str, dict[str, float]], corr.round(4).to_dict())
    return CorrelationResponse(
        correlation_matrix=correlation_matrix,
        diversification_score=round(div_score, 4),
        cluster_groups=groups,
    )


# ---------------------------------------------------------------------------
# Rolling metrics
# ---------------------------------------------------------------------------

def compute_rolling_metrics(req: RollingMetricsRequest) -> RollingMetricsResponse:
    if len(req.equity_curve) < 2:
        return RollingMetricsResponse(points=[], summary={})

    times = [p.time for p in req.equity_curve]
    equity = pd.Series(
        [p.equity for p in req.equity_curve],
        index=pd.to_datetime(times),
    )
    returns = equity.pct_change().dropna()
    window = max(req.window_days, 2)
    rf_daily = req.risk_free_rate / 252.0

    rolling = returns.rolling(window, min_periods=max(window // 2, 2))
    mean_ret = rolling.mean()
    std_ret = rolling.std()

    downside = returns.clip(upper=0.0)
    down_std = downside.rolling(window, min_periods=max(window // 2, 2)).std()

    rolling_sharpe = (mean_ret - rf_daily) / std_ret * np.sqrt(252)
    rolling_sortino = (mean_ret - rf_daily) / down_std.replace(0, np.nan) * np.sqrt(252)

    # Calmar: annualised return / |max rolling drawdown|
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.rolling(window, min_periods=1).max()
    drawdown = (cumulative - rolling_max) / rolling_max.replace(0, np.nan)
    rolling_max_dd = drawdown.rolling(window, min_periods=1).min().abs()
    ann_return = mean_ret * 252
    rolling_calmar = ann_return / rolling_max_dd.replace(0, np.nan)

    points: list[RollingMetricsPoint] = []
    for ts in returns.index:
        ts_value = pd.Timestamp(ts)
        s = rolling_sharpe.get(ts)
        so = rolling_sortino.get(ts)
        ca = rolling_calmar.get(ts)
        points.append(RollingMetricsPoint(
            time=ts_value.isoformat(),
            sharpe=None if (s is None or not np.isfinite(s)) else round(float(s), 4),
            sortino=None if (so is None or not np.isfinite(so)) else round(float(so), 4),
            calmar=None if (ca is None or not np.isfinite(ca)) else round(float(ca), 4),
        ))

    valid_sharpe = [p.sharpe for p in points if p.sharpe is not None]
    valid_sortino = [p.sortino for p in points if p.sortino is not None]
    summary = {
        "avg_sharpe": round(float(np.mean(valid_sharpe)), 4) if valid_sharpe else 0.0,
        "avg_sortino": round(float(np.mean(valid_sortino)), 4) if valid_sortino else 0.0,
    }

    return RollingMetricsResponse(points=points, summary=summary)


# ---------------------------------------------------------------------------
# Drawdown analysis
# ---------------------------------------------------------------------------

def compute_drawdown_analysis(req: DrawdownRequest) -> DrawdownResponse:
    if len(req.equity_curve) < 2:
        return DrawdownResponse(
            max_drawdown=0.0,
            avg_drawdown=0.0,
            periods=[],
            underwater_curve=[],
        )

    times = [p.time for p in req.equity_curve]
    equity = pd.Series(
        [p.equity for p in req.equity_curve],
        index=pd.to_datetime(times),
    )

    peak = equity.cummax()
    underwater = (equity - peak) / peak.replace(0, np.nan)
    max_dd = float(underwater.min())
    avg_dd = float(underwater[underwater < 0].mean()) if (underwater < 0).any() else 0.0

    underwater_curve = [{"time": str(t), "drawdown": round(float(v), 6)} for t, v in underwater.items()]

    # Identify distinct drawdown periods
    periods: list[DrawdownPeriod] = []
    in_dd = False
    start_idx = 0
    trough_idx = 0
    trough_val = 0.0
    ts_list = equity.index.tolist()

    for i, val in enumerate(underwater):
        if val < 0:
            if not in_dd:
                in_dd = True
                start_idx = i
                trough_idx = i
                trough_val = val
            elif val < trough_val:
                trough_idx = i
                trough_val = val
        else:
            if in_dd:
                start_ts = pd.Timestamp(ts_list[start_idx])
                trough_ts = pd.Timestamp(ts_list[trough_idx])
                end_ts = pd.Timestamp(ts_list[i])
                duration = (end_ts - start_ts).days
                recovery = (end_ts - trough_ts).days
                periods.append(DrawdownPeriod(
                    start=start_ts.isoformat(),
                    trough=trough_ts.isoformat(),
                    end=end_ts.isoformat(),
                    depth=round(float(trough_val), 6),
                    duration_days=int(max(duration, 0)),
                    recovery_days=int(max(recovery, 0)),
                ))
                in_dd = False

    # Open drawdown at end of series
    if in_dd:
        start_ts = pd.Timestamp(ts_list[start_idx])
        trough_ts = pd.Timestamp(ts_list[trough_idx])
        end_ts = pd.Timestamp(ts_list[-1])
        duration = (end_ts - start_ts).days
        periods.append(DrawdownPeriod(
            start=start_ts.isoformat(),
            trough=trough_ts.isoformat(),
            end=None,
            depth=round(float(trough_val), 6),
            duration_days=int(max(duration, 0)),
            recovery_days=None,
        ))

    # Sort by depth (worst first)
    periods.sort(key=lambda p: p.depth)

    return DrawdownResponse(
        max_drawdown=round(max_dd, 6),
        avg_drawdown=round(avg_dd, 6),
        periods=periods,
        underwater_curve=underwater_curve,
    )

# ---------------------------------------------------------------------------
# Optimization
# ---------------------------------------------------------------------------

def _hrp_weights(
    corr: np.ndarray,
    cov: np.ndarray,
    symbols: list[str],
) -> tuple[dict[str, float], list[str]]:
    """Hierarchical Risk Parity via recursive bisection (Lopez de Prado)."""
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform

    dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, None))
    np.fill_diagonal(dist, 0.0)
    link = linkage(squareform(dist), method="single")
    order = leaves_list(link).tolist()
    sorted_syms = [symbols[i] for i in order]

    def _ivp_var(cluster: list[str]) -> float:
        idxs = [symbols.index(s) for s in cluster]
        sub = cov[np.ix_(idxs, idxs)]
        ivp = 1.0 / np.maximum(np.diag(sub), 1e-12)
        ivp /= ivp.sum()
        return float(ivp @ sub @ ivp)

    weights: dict[str, float] = {s: 1.0 for s in symbols}

    def _bisect(items: list[str]) -> None:
        if len(items) <= 1:
            return
        mid = len(items) // 2
        left, right = items[:mid], items[mid:]
        var_l = _ivp_var(left)
        var_r = _ivp_var(right)
        alpha = 1.0 - var_l / (var_l + var_r + 1e-12)
        for s in left:
            weights[s] *= alpha
        for s in right:
            weights[s] *= 1.0 - alpha
        _bisect(left)
        _bisect(right)

    _bisect(sorted_syms)
    total = sum(weights.values())
    normed = {s: w / total for s, w in weights.items()}
    return normed, sorted_syms


async def compute_portfolio_optimization(req: OptimizeRequest) -> OptimizeResponse:
    if not req.symbols:
        return OptimizeResponse(weights={}, method=req.method)

    if len(req.symbols) == 1:
        return OptimizeResponse(weights={req.symbols[0]: 1.0}, method=req.method)

    # Fetch data
    tasks = [fetch_ohlcv_from_go(sym, req.timeframe, req.limit) for sym in req.symbols]
    fetched = await asyncio.gather(*tasks)
    assets = [a for a in fetched if a is not None and len(a.close) > 20]

    if not assets:
        return OptimizeResponse(weights={s: 1.0/len(req.symbols) for s in req.symbols}, method=req.method)

    # Simple heuristic fallback if data is too thin
    symbols = [a.symbol for a in assets]
    
    if req.method == "equal_weight" or len(assets) < 2:
        w = 1.0 / len(symbols)
        return OptimizeResponse(weights={s: w for s in symbols}, method="equal_weight")

    # Build returns
    min_len = min(len(a.close) for a in assets)
    data = {
        a.symbol: np.diff(np.log(np.array(a.close[-min_len:])))
        for a in assets
    }
    returns = pd.DataFrame(data)

    if req.method == "hrp":
        try:
            corr_arr = returns.corr().values
            cov_arr = returns.cov().values
            hrp_w, dendro_order = _hrp_weights(corr_arr, cov_arr, symbols)
            w_vec = np.array([hrp_w[s] for s in symbols])
            exp_vol = float(np.sqrt(w_vec @ cov_arr @ w_vec) * np.sqrt(252))
            return OptimizeResponse(
                weights=hrp_w,
                method="hrp",
                expected_volatility=round(exp_vol, 6),
                dendrogram_order=dendro_order,
            )
        except Exception:
            pass  # fall through to equal weight

    if req.method == "inverse_vol":
        vols = returns.std()
        inv_vols = 1.0 / vols.replace(0, np.nan).fillna(vols.mean())
        weights = inv_vols / inv_vols.sum()
        return OptimizeResponse(weights=weights.to_dict(), method="inverse_vol")

    if req.method == "min_variance":
        cov = returns.cov()
        inv_cov = np.linalg.pinv(cov.values)
        ones = np.ones(len(inv_cov))
        w = inv_cov @ ones
        w = w / w.sum()
        # Ensure non-negative weights (simple long-only constraint)
        w = np.clip(w, 0, None)
        w = w / w.sum()
        return OptimizeResponse(weights=dict(zip(symbols, w.tolist())), method="min_variance")

    # Default to equal weight
    w = 1.0 / len(symbols)
    return OptimizeResponse(weights={s: w for s in symbols}, method="equal_weight")


# ---------------------------------------------------------------------------
# Phase 13b — Kelly Multi-Asset
# ---------------------------------------------------------------------------

class KellyRequest(BaseModel):
    symbols: list[str]
    timeframe: str = "1D"
    limit: int = 252
    risk_fraction: float = 0.25  # half-Kelly default


class KellyResponse(BaseModel):
    allocations: dict[str, float]
    kelly_fractions: dict[str, float]
    portfolio_expected_return: float
    portfolio_variance: float


async def compute_kelly_allocation(req: KellyRequest) -> KellyResponse:
    if not req.symbols:
        return KellyResponse(
            allocations={},
            kelly_fractions={},
            portfolio_expected_return=0.0,
            portfolio_variance=0.0,
        )

    if len(req.symbols) == 1:
        sym = req.symbols[0]
        return KellyResponse(
            allocations={sym: req.risk_fraction},
            kelly_fractions={sym: 1.0},
            portfolio_expected_return=0.0,
            portfolio_variance=0.0,
        )

    tasks = [fetch_ohlcv_from_go(sym, req.timeframe, req.limit) for sym in req.symbols]
    fetched = await asyncio.gather(*tasks)
    assets = [a for a in fetched if a is not None and len(a.close) > 20]

    if not assets:
        n = len(req.symbols)
        return KellyResponse(
            allocations={s: req.risk_fraction / n for s in req.symbols},
            kelly_fractions={s: 1.0 / n for s in req.symbols},
            portfolio_expected_return=0.0,
            portfolio_variance=0.0,
        )

    symbols = [a.symbol for a in assets]
    min_len = min(len(a.close) for a in assets)
    returns_data = {
        a.symbol: np.diff(np.log(np.array(a.close[-min_len:])))
        for a in assets
    }
    returns_df = pd.DataFrame(returns_data)

    mean_ret: np.ndarray = np.asarray(returns_df.mean(), dtype=np.float64)
    cov: np.ndarray = np.asarray(returns_df.cov(), dtype=np.float64)

    try:
        kelly_raw = np.linalg.solve(cov + np.eye(len(cov)) * 1e-8, mean_ret)
    except np.linalg.LinAlgError:
        kelly_raw = np.zeros(len(symbols))

    kelly_scaled = kelly_raw * req.risk_fraction
    kelly_scaled = np.clip(kelly_scaled, 0.0, None)
    total = kelly_scaled.sum()
    allocations = (kelly_scaled / total * req.risk_fraction) if total > 0 else (
        np.ones(len(symbols)) / len(symbols) * req.risk_fraction
    )

    alloc_dict = {s: round(float(allocations[i]), 6) for i, s in enumerate(symbols)}
    kelly_fracs = {s: round(float(kelly_raw[i]), 6) for i, s in enumerate(symbols)}
    w = np.array([alloc_dict[s] for s in symbols])
    port_ret = float(w @ mean_ret * 252)
    port_var = float(w @ cov @ w * 252)

    return KellyResponse(
        allocations=alloc_dict,
        kelly_fractions=kelly_fracs,
        portfolio_expected_return=round(port_ret, 6),
        portfolio_variance=round(port_var, 6),
    )


# ---------------------------------------------------------------------------
# Phase 13c — Regime-Based Sizing
# ---------------------------------------------------------------------------

class RegimeSizingRequest(BaseModel):
    symbols: list[str]
    timeframe: str = "1D"
    limit: int = 100


class PositionSignal(BaseModel):
    symbol: str
    regime: Literal["bullish", "bearish", "ranging"]
    traffic_light: Literal["green", "yellow", "red"]
    recommended_size_pct: float
    confidence: float


class RegimeSizingResponse(BaseModel):
    signals: list[PositionSignal]
    portfolio_regime: Literal["risk_on", "neutral", "risk_off"]
    regime_confidence: float


async def compute_regime_sizing(req: RegimeSizingRequest) -> RegimeSizingResponse:
    tasks = [fetch_ohlcv_from_go(sym, req.timeframe, req.limit) for sym in req.symbols]
    fetched = await asyncio.gather(*tasks)

    signals: list[PositionSignal] = []
    regime_scores: list[float] = []
    n = len(req.symbols)
    equal_weight = 100.0 / n if n > 0 else 0.0

    for i, sym in enumerate(req.symbols):
        asset = fetched[i]
        if asset is None or len(asset.close) < 20:
            signals.append(PositionSignal(
                symbol=sym,
                regime="ranging",
                traffic_light="yellow",
                recommended_size_pct=round(equal_weight * 0.5, 2),
                confidence=0.3,
            ))
            regime_scores.append(0.0)
            continue

        closes = np.array(asset.close)
        sma_fast = float(np.mean(closes[-10:]))
        sma_slow = float(np.mean(closes[-30:])) if len(closes) >= 30 else float(np.mean(closes))
        slope_pct = (sma_fast - sma_slow) / (sma_slow + 1e-10)

        ret_window = np.diff(closes[-20:]) / (closes[-20:-1] + 1e-10)
        vol = float(np.std(ret_window))

        if slope_pct > 0.01:
            regime_label: Literal["bullish", "bearish", "ranging"] = "bullish"
            confidence = min(0.5 + abs(slope_pct) * 10.0, 0.95)
            regime_scores.append(confidence)
        elif slope_pct < -0.01:
            regime_label = "bearish"
            confidence = min(0.5 + abs(slope_pct) * 10.0, 0.95)
            regime_scores.append(-confidence)
        else:
            regime_label = "ranging"
            confidence = min(0.4 + vol * 5.0, 0.85)
            regime_scores.append(0.0)

        if regime_label == "bullish" and confidence > 0.6:
            traffic_light: Literal["green", "yellow", "red"] = "green"
            size_pct = equal_weight
        elif regime_label == "bearish":
            traffic_light = "red"
            size_pct = equal_weight * 0.15
        else:
            traffic_light = "yellow"
            size_pct = equal_weight * 0.5

        signals.append(PositionSignal(
            symbol=sym,
            regime=regime_label,
            traffic_light=traffic_light,
            recommended_size_pct=round(size_pct, 2),
            confidence=round(confidence, 4),
        ))

    if regime_scores:
        avg_score = float(np.mean(regime_scores))
        if avg_score > 0.2:
            portfolio_regime: Literal["risk_on", "neutral", "risk_off"] = "risk_on"
        elif avg_score < -0.2:
            portfolio_regime = "risk_off"
        else:
            portfolio_regime = "neutral"
        regime_confidence = round(min(abs(avg_score) / 0.5, 1.0), 4)
    else:
        portfolio_regime = "neutral"
        regime_confidence = 0.0

    return RegimeSizingResponse(
        signals=signals,
        portfolio_regime=portfolio_regime,
        regime_confidence=regime_confidence,
    )


# ---------------------------------------------------------------------------
# Phase 13d — Monte Carlo VaR
# ---------------------------------------------------------------------------

class MonteCarloRequest(BaseModel):
    weights: dict[str, float]
    symbols: list[str]
    timeframe: str = "1D"
    limit: int = 252
    simulations: int = 10_000
    horizon_days: int = 10
    confidence_levels: list[float] = Field(default_factory=lambda: [0.95, 0.99])


class MonteCarloResponse(BaseModel):
    var: dict[str, float]
    cvar: dict[str, float]
    median_return: float
    simulation_count: int


async def compute_monte_carlo_var(req: MonteCarloRequest) -> MonteCarloResponse:
    empty = MonteCarloResponse(
        var={str(c): 0.0 for c in req.confidence_levels},
        cvar={str(c): 0.0 for c in req.confidence_levels},
        median_return=0.0,
        simulation_count=0,
    )
    if not req.symbols:
        return empty

    tasks = [fetch_ohlcv_from_go(sym, req.timeframe, req.limit) for sym in req.symbols]
    fetched = await asyncio.gather(*tasks)
    assets = [a for a in fetched if a is not None and len(a.close) > 20]
    if not assets:
        return empty

    symbols = [a.symbol for a in assets]
    min_len = min(len(a.close) for a in assets)
    returns_data = {
        a.symbol: np.diff(np.log(np.array(a.close[-min_len:])))
        for a in assets
    }
    returns_df = pd.DataFrame(returns_data)
    mean_ret: np.ndarray = np.asarray(returns_df.mean(), dtype=np.float64)
    cov: np.ndarray = np.asarray(returns_df.cov(), dtype=np.float64)

    weights_vec = np.array([req.weights.get(s, 1.0 / len(symbols)) for s in symbols])
    weights_vec = weights_vec / (weights_vec.sum() + 1e-12)

    n_sims = min(req.simulations, 100_000)
    horizon = max(req.horizon_days, 1)

    try:
        L = np.linalg.cholesky(cov + np.eye(len(cov)) * 1e-8)
    except np.linalg.LinAlgError:
        L = np.diag(np.sqrt(np.maximum(np.diag(cov), 1e-10)))

    rng = np.random.default_rng(42)
    z = rng.standard_normal((n_sims, horizon, len(symbols)))
    sim_returns = z @ L.T + mean_ret  # (n_sims, horizon, n_assets)
    cum_returns = np.prod(1.0 + sim_returns, axis=1) - 1.0  # (n_sims, n_assets)
    portfolio_returns = cum_returns @ weights_vec  # (n_sims,)

    var_dict: dict[str, float] = {}
    cvar_dict: dict[str, float] = {}
    for conf in req.confidence_levels:
        pct = (1.0 - conf) * 100.0
        var_val = float(np.percentile(portfolio_returns, pct))
        tail = portfolio_returns[portfolio_returns <= var_val]
        cvar_val = float(tail.mean()) if len(tail) > 0 else var_val
        var_dict[str(conf)] = round(var_val, 6)
        cvar_dict[str(conf)] = round(cvar_val, 6)

    return MonteCarloResponse(
        var=var_dict,
        cvar=cvar_dict,
        median_return=round(float(np.median(portfolio_returns)), 6),
        simulation_count=n_sims,
    )


# ---------------------------------------------------------------------------
# Phase 13e — VPIN Risk Warning
# ---------------------------------------------------------------------------

class VPINRequest(BaseModel):
    symbol: str
    timeframe: str = "1D"
    limit: int = 50
    bucket_size: int = 10


class VPINResponse(BaseModel):
    vpin: float
    vpin_series: list[float]
    alert: bool
    threshold: float
    toxicity_level: Literal["low", "medium", "high"]


async def compute_vpin(req: VPINRequest) -> VPINResponse:
    threshold = 0.7
    empty = VPINResponse(
        vpin=0.0,
        vpin_series=[],
        alert=False,
        threshold=threshold,
        toxicity_level="low",
    )
    asset = await fetch_full_ohlcv_from_go(req.symbol, req.timeframe, req.limit)
    bucket_size = max(req.bucket_size, 1)
    if asset is None or len(asset.close) < bucket_size + 1:
        return empty

    closes = np.array(asset.close)
    highs = np.array(asset.high)
    lows = np.array(asset.low)
    volumes = np.array(asset.volume)

    range_ = highs - lows
    range_ = np.where(range_ == 0, 1e-10, range_)
    buy_frac = (closes - lows) / range_
    buy_vol = volumes * buy_frac
    sell_vol = volumes - buy_vol

    n_buckets = len(closes) // bucket_size
    if n_buckets == 0:
        return empty

    vpin_buckets: list[float] = []
    for i in range(n_buckets):
        s, e = i * bucket_size, (i + 1) * bucket_size
        bv = buy_vol[s:e].sum()
        sv = sell_vol[s:e].sum()
        total = bv + sv
        vpin_buckets.append(abs(bv - sv) / total if total > 0 else 0.0)

    window = min(10, len(vpin_buckets))
    current_vpin = float(np.mean(vpin_buckets[-window:]))
    alert = current_vpin > threshold
    toxicity: Literal["low", "medium", "high"] = (
        "high" if current_vpin >= 0.8 else "medium" if current_vpin >= threshold else "low"
    )

    return VPINResponse(
        vpin=round(current_vpin, 4),
        vpin_series=[round(v, 4) for v in vpin_buckets],
        alert=alert,
        threshold=threshold,
        toxicity_level=toxicity,
    )
