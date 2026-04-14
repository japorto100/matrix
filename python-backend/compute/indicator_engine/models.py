"""models.py — Pydantic request/response models for the indicator engine.

Extracted from pipeline.py (Phase A, 20.03.2026).
All models grouped by domain category.

Pydantic v2 conventions applied:
- Field() constraints on all numeric params (ge/le/gt)
- Literal types for closed enums (no raw strings)
- Response models: frozen=True where safe (immutable after creation)
- OHLCV validation via model_validator where meaningful
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Type Aliases (Literal enums)
# ---------------------------------------------------------------------------

SignalDirection = Literal["buy", "sell", "neutral"]
PatternDirection = Literal["bullish", "bearish", "neutral"]
ExoticMAType = Literal["kama", "alma", "iwma", "ols", "sma", "ema", "smma"]
ChartTransformType = Literal["heikin_ashi", "k_candles", "volume_candles", "carsi"]
VolatilityRegime = Literal["elevated", "normal", "compressed"]
SpikeWeightedRegime = Literal["very_quiet", "normal", "elevated", "high_volatility"]
MarketRegime = Literal["bullish", "bearish", "ranging"]
BarrierLabel = Literal["tp", "sl", "timeout"]
SignalLabel = Literal["buy", "sell", "hold"]
StressLevel = Literal["low", "medium", "high"]

# ---------------------------------------------------------------------------
# Reusable Field Constraints (Annotated — DRY across ~80 models)
# ---------------------------------------------------------------------------

Period = Annotated[int, Field(ge=2, le=500, description="Lookback period in bars")]
ShortPeriod = Annotated[int, Field(ge=2, le=200, description="Short lookback period")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
PositiveFloat = Annotated[float, Field(gt=0)]
StdMultiplier = Annotated[float, Field(ge=0.5, le=5.0, description="Standard deviation multiplier")]

# ---------------------------------------------------------------------------
# Core / Shared
# ---------------------------------------------------------------------------


class OHLCVPoint(BaseModel):
    """Single OHLCV bar. Fundamental data unit for all indicator functions."""

    model_config = ConfigDict(slots=True)
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def _validate_ohlcv(self) -> "OHLCVPoint":
        if self.high < self.low:
            msg = f"high ({self.high}) must be >= low ({self.low})"
            raise ValueError(msg)
        return self


def build_ohlcv(
    times: list[int],
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float] | None = None,
) -> list[OHLCVPoint]:
    """Build OHLCVPoint list from parallel arrays — skips validation (fast path).

    Use for trusted sources: Rust output, Polars DataFrames, Arrow columns, redb cache.
    """
    vols = volumes or [0.0] * len(times)
    return [
        OHLCVPoint.model_construct(time=t, open=o, high=h, low=lo, close=c, volume=v)
        for t, o, h, lo, c, v in zip(times, opens, highs, lows, closes, vols)
    ]


class IndicatorPoint(BaseModel):
    """Single time-value pair for indicator output."""

    model_config = ConfigDict(frozen=True, slots=True)
    time: int
    value: float


def build_points(times: list[int], values: list[float]) -> list[IndicatorPoint]:
    """Build IndicatorPoint list from parallel arrays — skips validation (3-5x faster).

    Use for trusted internal data (own calculations, Rust output, Polars columns).
    Do NOT use for external/user input.
    """
    return [
        IndicatorPoint.model_construct(time=t, value=v)
        for t, v in zip(times, values)
    ]


def build_response(
    times: list[int], values: list[float], metadata: dict[str, Any] | None = None
) -> "IndicatorResponse":
    """Build a complete IndicatorResponse from parallel arrays — fast path."""
    return IndicatorResponse(
        data=build_points(times, values),
        metadata=metadata or {},
    )


class IndicatorResponse(BaseModel):
    """Generic single-series indicator response."""

    data: list[IndicatorPoint]
    metadata: dict[str, Any]


class IndicatorServiceRequest(BaseModel):
    """Base request with OHLCV data + optional params."""

    ohlcv: list[OHLCVPoint] = Field(default_factory=list, min_length=2)
    params: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Trend / Moving Averages
# ---------------------------------------------------------------------------


class ExoticMARequest(IndicatorServiceRequest):
    maType: ExoticMAType = "kama"
    period: Period = 20
    alma_sigma: float = Field(default=6.0, ge=1.0, le=20.0)


class HMARequest(IndicatorServiceRequest):
    period: Period = 9


class IchimokuRequest(IndicatorServiceRequest):
    tenkan_period: int = Field(default=9, ge=2, le=100)
    kijun_period: int = Field(default=26, ge=2, le=200)
    senkou_b_period: int = Field(default=52, ge=2, le=500)
    displacement: int = Field(default=26, ge=1, le=200)
    include_future: bool = Field(default=True)


class IchimokuSignals(BaseModel):
    model_config = ConfigDict(frozen=True)
    above_cloud: list[bool]
    below_cloud: list[bool]
    in_cloud: list[bool]
    bullish_cloud: list[bool]
    tk_bull: list[bool]
    tk_bear: list[bool]
    chikou_bull: list[bool]
    chikou_bear: list[bool]
    chikou_above_cloud: list[bool]
    chikou_below_cloud: list[bool]
    kijun_cross_bull: list[bool]
    kijun_cross_bear: list[bool]
    strength: list[str]  # strong_bull / weak_bull / neutral / weak_bear / strong_bear


class IchimokuResponse(BaseModel):
    tenkan: list[IndicatorPoint]
    kijun: list[IndicatorPoint]
    span_a: list[IndicatorPoint]
    span_b: list[IndicatorPoint]
    chikou: list[IndicatorPoint]
    signals: IchimokuSignals
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Oscillators / Momentum
# ---------------------------------------------------------------------------


class MACDRequest(IndicatorServiceRequest):
    fast: ShortPeriod = 12
    slow: ShortPeriod = 26
    signal: ShortPeriod = 9

    @model_validator(mode="after")
    def _fast_lt_slow(self) -> "MACDRequest":
        if self.fast >= self.slow:
            msg = f"fast ({self.fast}) must be < slow ({self.slow})"
            raise ValueError(msg)
        return self


class MACDResponse(BaseModel):
    macd_line: list[IndicatorPoint]
    signal_line: list[IndicatorPoint]
    histogram: list[IndicatorPoint]
    metadata: dict[str, Any]


class StochasticRequest(IndicatorServiceRequest):
    k_period: int = Field(default=14, ge=2, le=200)
    d_period: int = Field(default=3, ge=2, le=50)


class StochasticResponse(BaseModel):
    k: list[IndicatorPoint]
    d: list[IndicatorPoint]
    metadata: dict[str, Any]


class ADXRequest(IndicatorServiceRequest):
    period: ShortPeriod = 14


class ADXResponse(BaseModel):
    adx: list[IndicatorPoint]
    di_plus: list[IndicatorPoint]
    di_minus: list[IndicatorPoint]
    metadata: dict[str, Any]


class RSIVariantRequest(IndicatorServiceRequest):
    rsiPeriod: int = Field(default=14, ge=2, le=200)
    atrPeriod: int = Field(default=14, ge=2, le=200)


class CompositeSignalRequest(IndicatorServiceRequest):
    heartbeatThreshold: float = Field(default=0.7, ge=0.0, le=1.0)
    volumeSpikeThreshold: float = Field(default=1.5, ge=0.5, le=10.0)


class CompositeComponent(BaseModel):
    model_config = ConfigDict(frozen=True)
    score: Confidence
    details: dict[str, Any] = Field(default_factory=dict)


class CompositeSignalResponse(BaseModel):
    signal: SignalDirection
    confidence: Confidence
    components: dict[str, CompositeComponent]
    timestamp: int


# ---------------------------------------------------------------------------
# K's Collection (Kaabar proprietary)
# ---------------------------------------------------------------------------


class KsCollectionRequest(IndicatorServiceRequest):
    period: int = Field(default=14, ge=2, le=200)


# ---------------------------------------------------------------------------
# Rainbow Collection (Kaabar proprietary)
# ---------------------------------------------------------------------------


class RainbowRequest(IndicatorServiceRequest):
    """Request for the full 7-indicator Rainbow Collection (Kaabar 2026)."""

    pass


class RainbowSignalSeries(BaseModel):
    data: list[IndicatorPoint]  # 1.0 bullish | -1.0 bearish | 0.0 neutral
    metadata: dict[str, Any]


class RainbowResponse(BaseModel):
    red: RainbowSignalSeries
    orange: RainbowSignalSeries
    yellow: RainbowSignalSeries
    green: RainbowSignalSeries
    blue: RainbowSignalSeries
    indigo: RainbowSignalSeries
    violet: RainbowSignalSeries


class RPatternRequest(IndicatorServiceRequest):
    """R-Pattern reversal detector (Kaabar 2026, Ch. 7)."""

    rsi_period: int = Field(default=14, ge=2, le=100)


class RPatternResponse(BaseModel):
    data: list[IndicatorPoint]  # 1.0 bullish | -1.0 bearish | 0.0 neutral
    metadata: dict[str, Any]


class GapPatternRequest(IndicatorServiceRequest):
    """Gap-Pattern detector (Kaabar 2026, Ch. 10).

    min_size: ATR multiplier — only gaps > ATR * min_size are tradeable.
    """

    atr_period: int = Field(default=14, ge=2, le=100)
    min_size: float = Field(default=1.0, ge=0.1, le=10.0)


class GapPatternResponse(BaseModel):
    data: list[IndicatorPoint]  # 1.0 bullish gap-fill | -1.0 bearish | 0.0 none
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Volatility / Bands
# ---------------------------------------------------------------------------


class BollingerVariantRequest(IndicatorServiceRequest):
    period: Period = 20
    numStd: StdMultiplier = 2.0


class BollingerSqueezeRequest(IndicatorServiceRequest):
    bbPeriod: ShortPeriod = 20
    kcPeriod: ShortPeriod = 20
    kcMult: float = Field(default=1.5, ge=0.5, le=4.0)
    numStd: StdMultiplier = 2.0


class BollingerSqueezeResponse(BaseModel):
    squeeze: list[bool]
    histogram: list[IndicatorPoint]
    metadata: dict[str, Any]


class BollingerOnRSIResponse(BaseModel):
    upper: list[IndicatorPoint]
    mid: list[IndicatorPoint]
    lower: list[IndicatorPoint]
    metadata: dict[str, Any]


class KeltnerRequest(IndicatorServiceRequest):
    ema_period: int = Field(default=20, ge=2, le=200)
    atr_period: int = Field(default=10, ge=2, le=200)
    multiplier: float = Field(default=2.0, ge=0.5, le=5.0)


class KeltnerResponse(BaseModel):
    upper: list[IndicatorPoint]
    middle: list[IndicatorPoint]
    lower: list[IndicatorPoint]
    metadata: dict[str, Any]


class VWAPRequest(IndicatorServiceRequest):
    pass


class VolatilitySuiteRequest(BaseModel):
    closes: list[float] = Field(min_length=10)
    lookback: int = Field(default=20, ge=5, le=500)


class VolatilitySuiteResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    spike_weighted_vol: float
    volatility_index: float
    exp_weighted_stddev: float
    volatility_regime: VolatilityRegime
    spike_weighted_regime: SpikeWeightedRegime


# ---------------------------------------------------------------------------
# Regime Detection
# ---------------------------------------------------------------------------


class RegimeDetectRequest(BaseModel):
    closes: list[float] = Field(min_length=20)
    lookback: int = Field(default=100, ge=20, le=1000)
    n_components: int = Field(default=3, ge=2, le=6)


class RegimeDetectResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    current_regime: MarketRegime
    sma_slope: float
    adx: float
    confidence: float


class MarkovRegimeResponse(BaseModel):
    current_regime: str
    transition_probs: dict[str, float]
    expected_duration: float
    shift_probability: float
    stationary_distribution: dict[str, float]
    warning: str | None


class HMMRegimeResponse(BaseModel):
    n_components: int
    hidden_state: int
    state_labels: list[str]
    means: list[float]
    bic_score: float


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------


class PatternRequest(IndicatorServiceRequest):
    lookback: int = Field(default=250, ge=20, le=5000)
    threshold: float = Field(default=0.015, ge=0.001, le=0.2)
    slanted_neckline: bool = Field(default=False)


class PatternData(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)
    type: str
    direction: PatternDirection
    start_time: int
    end_time: int
    confidence: Confidence
    details: dict[str, Any] = Field(default_factory=dict)


class PatternResponse(BaseModel):
    patterns: list[PatternData]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Pivot:
    """Lightweight pivot point used internally by swing detection and pattern algos."""
    index: int
    time: int
    price: float
    kind: Literal["high", "low"]


class SwingPoint(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)
    index: int
    time: int
    price: float
    kind: Literal["high", "low"]


class SwingDetectRequest(IndicatorServiceRequest):
    window: int = Field(default=3, ge=1, le=20)


class SwingDetectResponse(BaseModel):
    swings: list[SwingPoint]
    metadata: dict[str, Any]


class FibonacciLevel(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)
    ratio: float
    price: float


class FibonacciResponse(BaseModel):
    swing: dict[str, Any]
    levels: list[FibonacciLevel]


class FibonacciConfluenceRequest(IndicatorServiceRequest):
    thresholdPct: float = Field(default=0.005, ge=0.001, le=0.05)
    numSwings: int = Field(default=3, ge=2, le=10)


class ConfluenceZone(BaseModel):
    model_config = ConfigDict(frozen=True)
    priceCenter: float
    priceRange: tuple[float, float]
    levels: list[FibonacciLevel]
    strength: int


class FibonacciConfluenceResponse(BaseModel):
    zones: list[ConfluenceZone]
    metadata: dict[str, Any]


class TDCountdownState(TypedDict):
    kind: Literal["bullish", "bearish"]
    start_idx: int
    tdst: float


# ---------------------------------------------------------------------------
# Chart Transforms
# ---------------------------------------------------------------------------


class ChartTransformRequest(IndicatorServiceRequest):
    transformType: ChartTransformType = "heikin_ashi"


class ChartTransformResponse(BaseModel):
    data: list[OHLCVPoint]
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Strategy / Portfolio
# ---------------------------------------------------------------------------


class TradeInput(BaseModel):
    entry: float = Field(gt=0)
    exit: float = Field(gt=0)
    quantity: float = Field(default=1.0, gt=0)
    side: Literal["long", "short"] = "long"
    fee: float = Field(default=0.0, ge=0.0)


class EvaluateStrategyRequest(BaseModel):
    trades: list[TradeInput] = Field(default_factory=list)
    riskFreeRate: float = 0.0


class StrategyMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    net_return: float
    hit_ratio: float
    risk_reward_ratio: float
    expectancy: float
    profit_factor: float
    sharpe: float
    sortino: float
    average_win: float
    average_loss: float


class StrategyEvaluationResponse(BaseModel):
    metrics: StrategyMetrics
    tradeCount: int


class PerformanceMetricsRequest(BaseModel):
    returns: list[float] = Field(min_length=2)
    riskFreeRate: float = 0.0


class PerformanceMetricsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    net_return: float
    hit_ratio: float
    profit_factor: float
    sharpe: float
    sortino: float
    max_drawdown: float


# ---------------------------------------------------------------------------
# Backtest / Walk-Forward
# ---------------------------------------------------------------------------


class BacktestRequest(BaseModel):
    closes: list[float] = Field(min_length=10)
    lookback: int = Field(default=10, ge=2, le=200)
    slippage_bps: float = Field(default=0.0, ge=0.0, le=500.0)
    commission_bps: float = Field(default=0.0, ge=0.0, le=500.0)


class BacktestResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    strategy_returns: list[float]
    cumulative_return: float
    trade_count: int


class TripleBarrierRequest(BaseModel):
    closes: list[float] = Field(min_length=20)
    horizon: int = Field(default=10, ge=2, le=100)
    take_profit: float = Field(default=0.03, ge=0.005, le=0.5)
    stop_loss: float = Field(default=0.02, ge=0.005, le=0.5)


class TripleBarrierResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    labels: list[BarrierLabel]
    tp_count: int
    sl_count: int
    timeout_count: int


class ParameterSensitivityRequest(BaseModel):
    closes: list[float] = Field(min_length=40)
    lookbacks: list[int] = Field(min_length=2)


class ParameterSensitivityResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    by_lookback: dict[str, float]
    stability_score: float


class WalkForwardRequest(BaseModel):
    closes: list[float] = Field(min_length=60)
    train_window: int = Field(default=40, ge=20, le=1000)
    test_window: int = Field(default=10, ge=5, le=200)


class WalkForwardResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    oos_scores: list[float]
    mean_oos_score: float
    stability_score: float


class DeflatedSharpeRequest(BaseModel):
    sharpe: float
    trials: int = Field(default=10, ge=1, le=10000)
    sample_length: int = Field(default=252, ge=20, le=100000)


class DeflatedSharpeResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    deflated_sharpe: float
    pass_gate: bool


class EvalBaselineRequest(BaseModel):
    closes: list[float] = Field(min_length=40)
    horizon: int = Field(default=10, ge=2, le=100)
    take_profit: float = Field(default=0.03, ge=0.005, le=0.5)
    stop_loss: float = Field(default=0.02, ge=0.005, le=0.5)


class EvalBaselineResponse(BaseModel):
    labels: list[BarrierLabel]
    hit_ratio: float
    expectancy: float
    regime: str
    precision_proxy: float
    recall_proxy: float
    f1_proxy: float


class EvalIndicatorRequest(BaseModel):
    closes: list[float] = Field(min_length=80)


class EvalIndicatorResponse(BaseModel):
    walk_forward: WalkForwardResponse
    baseline: EvalBaselineResponse
    deflated_sharpe: DeflatedSharpeResponse
    execution_realism_pass: bool
    gate_pass: bool


# ---------------------------------------------------------------------------
# Quant / Heuristic Classifiers (NOT real ML — no trained models)
# ---------------------------------------------------------------------------


class FeatureEngineeringRequest(IndicatorServiceRequest):
    period: int = Field(default=14, ge=2, le=200)


class FeatureEngineeringResponse(BaseModel):
    features: list[dict[str, float]]
    feature_names: list[str]


class MLClassifySignalRequest(BaseModel):
    features: dict[str, float]


class MLClassifySignalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: SignalLabel
    score: float


class HybridFusionRequest(BaseModel):
    ml_score: float = Field(ge=0.0, le=1.0)
    rule_score: float = Field(ge=0.0, le=1.0)
    ml_weight: float = Field(default=0.6, ge=0.0, le=1.0)


class HybridFusionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    fused_score: float
    action: SignalLabel


class BiasMonitoringRequest(BaseModel):
    geographic_distribution: dict[str, int]
    regime_distribution: dict[str, int]
    agreement_rate: float = Field(ge=0.0, le=1.0)


class BiasMonitoringResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    geographic_imbalance: float
    regime_imbalance: float
    agreement_rate: float
    alert: bool


class SignalQualityChainRequest(BaseModel):
    labels: list[Literal["strong", "weak", "invalid"]] = Field(min_length=2)


class SignalQualityChainResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    transition: dict[str, dict[str, float]]
    quality_score: float


class OrderFlowStateRequest(BaseModel):
    buy_volumes: list[float] = Field(min_length=3)
    sell_volumes: list[float] = Field(min_length=3)
    squeeze_threshold: float = Field(default=0.1, ge=0.01, le=1.0)


class OrderFlowStateResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    states: list[Literal["accumulation", "distribution", "squeeze"]]
    dominant_state: Literal["accumulation", "distribution", "squeeze"]


class AlternativeBarsRequest(IndicatorServiceRequest):
    bucketSize: int = Field(default=20, ge=2, le=500)


class AlternativeBarsResponse(BaseModel):
    volume_bar_closes: list[float]
    dollar_bar_closes: list[float]
    tick_bar_closes: list[float]
    metadata: dict[str, Any]


class CUSUMRequest(BaseModel):
    closes: list[float] = Field(min_length=10)
    threshold: float = Field(default=0.02, ge=0.001, le=1.0)


class CUSUMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    break_indices: list[int]
    break_signals: list[str]
    cumulative_pos: float
    cumulative_neg: float


class MeanRevMomentumRequest(BaseModel):
    closes: list[float] = Field(min_length=30)


class MeanRevMomentumResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    hurst: float
    adf_proxy_stat: float
    half_life: float
    classification: Literal["mean_reverting", "momentum", "random_walk"]


# ---------------------------------------------------------------------------
# Derivatives / Market Microstructure
# ---------------------------------------------------------------------------


class DarkPoolSignalRequest(BaseModel):
    lit_volume: float = Field(gt=0)
    dark_pool_volume: float = Field(ge=0)


class DarkPoolSignalResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    dark_pool_ratio: float
    signal: Literal["accumulation", "distribution", "neutral"]
    confidence: float


class GEXProfileRequest(BaseModel):
    strikes: list[float] = Field(min_length=1)
    call_gamma: list[float] = Field(min_length=1)
    put_gamma: list[float] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_list_parity(self) -> "GEXProfileRequest":
        n = len(self.strikes)
        if len(self.call_gamma) != n or len(self.put_gamma) != n:
            raise ValueError("strikes, call_gamma, put_gamma must have equal length")
        return self


class GEXProfileResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    net_gex: list[float]
    call_wall: float
    put_wall: float


class ExpectedMoveRequest(BaseModel):
    spot: float = Field(gt=0)
    iv_annual: float = Field(ge=0.0, le=5.0)
    days: int = Field(default=7, ge=1, le=365)


class ExpectedMoveResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    move_abs: float
    upper: float
    lower: float


class OptionLeg(BaseModel):
    kind: Literal["call", "put"]
    strike: float = Field(gt=0)
    premium: float = Field(ge=0)
    quantity: int = Field(default=1)


class OptionsCalculatorRequest(BaseModel):
    spot: float = Field(gt=0)
    legs: list[OptionLeg] = Field(min_length=1)
    underlying_qty: int = 100


class OptionsCalculatorResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    max_profit: float
    max_loss: float
    breakevens: list[float]


class DeFiStressRequest(BaseModel):
    tvl_change_pct: float
    funding_rate: float
    open_interest_change_pct: float


class DeFiStressResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    stress_score: float
    level: StressLevel


class OracleCrossCheckRequest(BaseModel):
    web2_price: float = Field(gt=0)
    oracle_price: float = Field(gt=0)
    threshold_pct: float = Field(default=0.01, ge=0.001, le=0.2)


class OracleCrossCheckResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    divergence_pct: float
    disagreement: bool
    severity: StressLevel


# ---------------------------------------------------------------------------
# Rob Booker Reversal (Kaabar 2026, Ch. 12)
# ---------------------------------------------------------------------------


class RobBookerReversalRequest(IndicatorServiceRequest):
    """Rob Booker Reversal: Stochastic(70,10,10) + MACD(12,26,9) zero-cross."""

    stoch_k_period: int = Field(default=70, ge=5, le=200)
    stoch_smooth_k: int = Field(default=10, ge=1, le=50)
    stoch_d_period: int = Field(default=10, ge=1, le=50)
    macd_fast: int = Field(default=12, ge=2, le=50)
    macd_slow: int = Field(default=26, ge=5, le=100)
    macd_signal: int = Field(default=9, ge=2, le=50)
    stoch_lower: float = Field(default=30.0, ge=5.0, le=50.0)
    stoch_upper: float = Field(default=70.0, ge=50.0, le=95.0)


# ---------------------------------------------------------------------------
# Cross-Asset Convergence (Kaabar 2026, Ch. 6 — VIX-RSI paradigm)
# ---------------------------------------------------------------------------


class CrossAssetConvergenceRequest(BaseModel):
    """RSI convergence across inversely-correlated assets (e.g. SPX + VIX)."""

    primary_closes: list[float] = Field(min_length=20)
    inverse_closes: list[float] = Field(min_length=20)
    rsi_period: int = Field(default=14, ge=2, le=100)
    lower: float = Field(default=30.0, ge=5.0, le=50.0)
    upper: float = Field(default=70.0, ge=50.0, le=95.0)


class CrossAssetConvergenceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    signals: list[float]  # 1.0 bullish convergence | -1.0 bearish | 0.0 none
    primary_rsi: list[float]
    inverse_rsi: list[float]
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Swarming — Multi-Chart-System Validation (Kaabar 2026, Kap. 4/9/11)
# ---------------------------------------------------------------------------


class SwarmValidationRequest(IndicatorServiceRequest):
    """Run pattern detection on Standard + HA + K's CCS, return swarmed signals."""

    pattern_type: Literal["candlestick", "timing", "price"] = "timing"
    lookback: int = Field(default=250, ge=20, le=5000)
    threshold: float = Field(default=0.015, ge=0.001, le=0.2)


class SwarmSignal(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: str
    direction: PatternDirection
    start_time: int
    end_time: int
    swarming_ratio: float  # 0.33, 0.67, or 1.0
    fired_on: list[Literal["standard", "heikin_ashi", "k_candles"]]
    confidence: float  # original confidence × swarming_ratio


class SwarmValidationResponse(BaseModel):
    signals: list[SwarmSignal]
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Regime Weighting (Kaabar 2026, Ch. 1 — fundamental principle)
# ---------------------------------------------------------------------------

RegimeWeightMode = Literal["multiply", "filter"]


class RegimeWeightConfig(BaseModel):
    """Configuration for regime-aware signal weighting."""

    model_config = ConfigDict(frozen=True)
    boost_aligned: float = Field(default=1.3, ge=1.0, le=2.0)
    dampen_opposed: float = Field(default=0.7, ge=0.3, le=1.0)
    filter_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    mode: RegimeWeightMode = "multiply"


# ---------------------------------------------------------------------------
# RSI Signal Techniques (Kaabar 2026, Ch. 3)
# ---------------------------------------------------------------------------


class RSIVTechniqueRequest(IndicatorServiceRequest):
    """RSI V-Technique: RSI(5), barriers 15/85, V-bounce detection."""

    rsi_period: int = Field(default=5, ge=2, le=50)
    lower: float = Field(default=15.0, ge=5.0, le=40.0)
    upper: float = Field(default=85.0, ge=60.0, le=95.0)


class RSIDCCRequest(IndicatorServiceRequest):
    """RSI Double Conservative Confirmation: dual-RSI(13,34) simultaneous cross."""

    fast_period: int = Field(default=13, ge=2, le=50)
    slow_period: int = Field(default=34, ge=5, le=100)
    lower: float = Field(default=30.0, ge=10.0, le=50.0)
    upper: float = Field(default=70.0, ge=50.0, le=90.0)
    tolerance: int = Field(default=0, ge=0, le=2)


class RSIMACrossRequest(IndicatorServiceRequest):
    """RSI MA Cross: RSI crosses its own SMA while in extreme zone."""

    rsi_period: int = Field(default=5, ge=2, le=50)
    sma_period: int = Field(default=5, ge=2, le=50)
    lower: float = Field(default=25.0, ge=5.0, le=50.0)
    upper: float = Field(default=75.0, ge=50.0, le=95.0)


# ---------------------------------------------------------------------------
# BB Signal Techniques (Kaabar 2026, Ch. 3)
# ---------------------------------------------------------------------------


class BBTrendFriendlyRequest(IndicatorServiceRequest):
    """BB Trend-Friendly: Conservative signal + SMA(100) trend filter."""

    bb_period: int = Field(default=20, ge=5, le=100)
    num_std: float = Field(default=2.0, ge=0.5, le=4.0)
    sma_period: int = Field(default=100, ge=20, le=500)
    sma_offset: int = Field(default=10, ge=0, le=50)


# ---------------------------------------------------------------------------
# WMA/IWMA Cross (Kaabar 2026, Ch. 3)
# ---------------------------------------------------------------------------


class WMAIWMACrossRequest(IndicatorServiceRequest):
    """WMA/IWMA single-parameter cross: same period, opposite weighting bias."""

    period: Period = 20
