from __future__ import annotations

import hashlib
import json as _json
from typing import Any

from fastapi.responses import JSONResponse
from shared import create_service_app
from shared.cache_adapter import create_cache_adapter, TTL_INDICATOR
# --- Models (request/response types) ---
from .models import (
    ADXRequest,
    ADXResponse,
    AlternativeBarsRequest,
    AlternativeBarsResponse,
    BacktestRequest,
    BacktestResponse,
    BiasMonitoringRequest,
    BiasMonitoringResponse,
    BollingerOnRSIResponse,
    BollingerSqueezeRequest,
    BollingerSqueezeResponse,
    BollingerVariantRequest,
    ChartTransformRequest,
    ChartTransformResponse,
    CompositeSignalRequest,
    CompositeSignalResponse,
    ConfluenceZone,  # noqa: F401 — re-exported for schema inference
    CUSUMRequest,
    CUSUMResponse,
    DarkPoolSignalRequest,
    DarkPoolSignalResponse,
    DeflatedSharpeRequest,
    DeflatedSharpeResponse,
    DeFiStressRequest,
    DeFiStressResponse,
    EvalBaselineRequest,
    EvalBaselineResponse,
    EvalIndicatorRequest,
    EvalIndicatorResponse,
    EvaluateStrategyRequest,
    ExoticMARequest,
    ExpectedMoveRequest,
    ExpectedMoveResponse,
    FeatureEngineeringRequest,
    FeatureEngineeringResponse,
    FibonacciConfluenceRequest,
    FibonacciConfluenceResponse,
    FibonacciResponse,
    GEXProfileRequest,
    GEXProfileResponse,
    HMARequest,
    HMMRegimeResponse,
    HybridFusionRequest,
    HybridFusionResponse,
    IchimokuRequest,
    IchimokuResponse,
    IndicatorResponse,
    KeltnerRequest,
    KeltnerResponse,
    KsCollectionRequest,
    MACDRequest,
    MACDResponse,
    MarkovRegimeResponse,
    MeanRevMomentumRequest,
    MeanRevMomentumResponse,
    MLClassifySignalRequest,
    MLClassifySignalResponse,
    OptionLeg,  # noqa: F401
    OptionsCalculatorRequest,
    OptionsCalculatorResponse,
    OracleCrossCheckRequest,
    OracleCrossCheckResponse,
    OrderFlowStateRequest,
    OrderFlowStateResponse,
    ParameterSensitivityRequest,
    ParameterSensitivityResponse,
    PatternRequest,
    PatternResponse,
    PerformanceMetricsRequest,
    PerformanceMetricsResponse,
    BBTrendFriendlyRequest,
    CrossAssetConvergenceRequest,
    CrossAssetConvergenceResponse,
    GapPatternRequest,
    GapPatternResponse,
    RPatternRequest,
    RPatternResponse,
    RSIDCCRequest,
    RSIMACrossRequest,
    RSIVTechniqueRequest,
    RainbowRequest,
    RainbowResponse,
    RSIVariantRequest,
    WMAIWMACrossRequest,
    RegimeDetectRequest,
    RegimeDetectResponse,
    RobBookerReversalRequest,
    SignalQualityChainRequest,
    SignalQualityChainResponse,
    StochasticRequest,
    StochasticResponse,
    StrategyEvaluationResponse,
    SwarmValidationRequest,
    SwarmValidationResponse,
    SwingDetectRequest,
    SwingDetectResponse,
    TripleBarrierRequest,
    TripleBarrierResponse,
    VolatilitySuiteRequest,
    VolatilitySuiteResponse,
    VWAPRequest,
    WalkForwardRequest,
    WalkForwardResponse,
)
# --- Pattern detection ---
from .patterns import (
    apply_chart_transform,
    build_candlestick_patterns,
    build_elliott_wave_patterns,
    build_fibonacci_confluence,
    build_fibonacci_levels,
    build_harmonic_patterns,
    build_price_patterns,
    build_strategy_metrics,
    build_td_timing_patterns,
    calculate_swing_points,
)
# --- Volatility ---
from .volatility import (
    calculate_atr_rsi,
    calculate_bb_aggressive,
    calculate_bb_bandwidth,
    calculate_bb_conservative,
    calculate_bb_percent_b,
    calculate_bb_trend_friendly,
    calculate_bollinger_keltner_squeeze,
    calculate_bollinger_on_rsi,
    calculate_hmm_regime,
    calculate_keltner,
    calculate_markov_regime,
    calculate_regime,
    calculate_volatility_suite,
)
# --- Oscillators ---
from .oscillators import (
    build_composite_signal,
    calculate_adx,
    calculate_cross_asset_convergence,
    calculate_ks_collection,
    calculate_macd,
    calculate_rob_booker_reversal,
    calculate_rsi_dcc,
    calculate_rsi_ma_cross,
    calculate_rsi_v_technique,
    calculate_stochastic,
)
# --- Trend ---
from .trend import (
    calculate_exotic_ma,
    calculate_hma,
    calculate_ichimoku,
    calculate_wma_iwma_cross,
)
# --- Volume ---
from .volume import calculate_vwap
# --- Quant / ML ---
from .quant import (
    build_features,
    calculate_alternative_bars,
    calculate_cusum,
    calculate_deflated_sharpe,
    calculate_eval_baseline,
    calculate_meanrev_momentum,
    calculate_order_flow_state,
    calculate_performance_metrics,
    calculate_signal_quality_chain,
    classify_signal,
    evaluate_indicator,
    fuse_hybrid,
    monitor_bias,
)
# --- Derivatives ---
from .derivatives import (
    calculate_dark_pool_signal,
    calculate_defi_stress,
    calculate_expected_move,
    calculate_gex_profile,
    calculate_options_payoff,
    calculate_oracle_crosscheck,
)
# --- Backtest ---
from .backtest import (
    calculate_triple_barrier,
    run_backtest,
    run_parameter_sensitivity,
    run_walk_forward,
)
# --- Helpers ---
from .helpers import indicator_dataframe_status, swarm_validate
# --- Rainbow ---
from .rainbow import (
    calculate_gap_pattern,
    calculate_r_pattern,
    calculate_rainbow_collection,
    calculate_rainbow_confluence,
    rainbow_composite_score,
)
# --- Regime Weighting ---
from .regime_weighting import regime_weight_patterns
from .rust_bridge import rust_core_status
from .portfolio_analytics import (
    CorrelationRequest,
    DrawdownRequest,
    KellyRequest,
    MonteCarloRequest,
    OptimizeRequest,
    RegimeSizingRequest,
    RollingMetricsRequest,
    VPINRequest,
    compute_correlations,
    compute_drawdown_analysis,
    compute_kelly_allocation,
    compute_monte_carlo_var,
    compute_portfolio_optimization,
    compute_regime_sizing,
    compute_rolling_metrics,
    compute_vpin,
)


app = create_service_app("indicator-service", http_port=8092)

_indicator_cache = None


def _cache():
    global _indicator_cache
    if _indicator_cache is None:
        _indicator_cache = create_cache_adapter()
    return _indicator_cache


def _body_key(prefix: str, body: dict) -> str:
    h = hashlib.md5(_json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return f"tradeview:indicator:{prefix}:{h}"


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "rustCore": rust_core_status(), "dataframe": indicator_dataframe_status()}


@app.post("/api/v1/indicators/exotic-ma")
def indicators_exotic_ma(payload: ExoticMARequest):
    return calculate_exotic_ma(payload)


@app.post("/api/v1/indicators/ks-collection")
def indicators_ks_collection(payload: KsCollectionRequest):
    return calculate_ks_collection(payload)


@app.post("/api/v1/patterns/candlestick", response_model=PatternResponse)
async def patterns_candlestick(payload: PatternRequest) -> Any:
    ck = _body_key("candlestick", payload.model_dump())
    hit = await _cache().get(ck)
    if hit is not None:
        return JSONResponse(hit)
    result = build_candlestick_patterns(payload)
    result_data = result.model_dump()
    await _cache().set(ck, result_data, ttl_seconds=TTL_INDICATOR)
    return JSONResponse(result_data)


@app.post("/api/v1/patterns/harmonic", response_model=PatternResponse)
async def patterns_harmonic(payload: PatternRequest) -> Any:
    ck = _body_key("harmonic", payload.model_dump())
    hit = await _cache().get(ck)
    if hit is not None:
        return JSONResponse(hit)
    result = build_harmonic_patterns(payload)
    result_data = result.model_dump()
    await _cache().set(ck, result_data, ttl_seconds=TTL_INDICATOR)
    return JSONResponse(result_data)


@app.post("/api/v1/patterns/timing", response_model=PatternResponse)
def patterns_timing(payload: PatternRequest) -> PatternResponse:
    return build_td_timing_patterns(payload)


@app.post("/api/v1/patterns/price", response_model=PatternResponse)
async def patterns_price(payload: PatternRequest) -> Any:
    ck = _body_key("price", payload.model_dump())
    hit = await _cache().get(ck)
    if hit is not None:
        return JSONResponse(hit)
    result = build_price_patterns(payload)
    result_data = result.model_dump()
    await _cache().set(ck, result_data, ttl_seconds=TTL_INDICATOR)
    return JSONResponse(result_data)


@app.post("/api/v1/patterns/elliott-wave", response_model=PatternResponse)
async def patterns_elliott_wave(payload: PatternRequest) -> Any:
    ck = _body_key("elliott-wave", payload.model_dump())
    hit = await _cache().get(ck)
    if hit is not None:
        return JSONResponse(hit)
    result = build_elliott_wave_patterns(payload)
    result_data = result.model_dump()
    await _cache().set(ck, result_data, ttl_seconds=TTL_INDICATOR)
    return JSONResponse(result_data)


@app.post("/api/v1/signals/composite", response_model=CompositeSignalResponse)
def signals_composite(payload: CompositeSignalRequest) -> CompositeSignalResponse:
    return build_composite_signal(payload)


@app.post("/api/v1/evaluate/strategy", response_model=StrategyEvaluationResponse)
def evaluate_strategy(payload: EvaluateStrategyRequest) -> StrategyEvaluationResponse:
    return build_strategy_metrics(payload)


@app.post("/api/v1/fibonacci/levels", response_model=FibonacciResponse)
def fibonacci_levels(payload: PatternRequest) -> FibonacciResponse:
    return build_fibonacci_levels(payload)


@app.post("/api/v1/charting/transform", response_model=ChartTransformResponse)
def charting_transform(payload: ChartTransformRequest) -> ChartTransformResponse:
    return apply_chart_transform(payload)


# Phase 5b: Portfolio Analytics
@app.post("/api/v1/portfolio/correlations")
async def portfolio_correlations(payload: CorrelationRequest):
    return await compute_correlations(payload)


@app.post("/api/v1/portfolio/rolling-metrics")
def portfolio_rolling_metrics(payload: RollingMetricsRequest):
    return compute_rolling_metrics(payload)


@app.post("/api/v1/portfolio/drawdown-analysis")
def portfolio_drawdown_analysis(payload: DrawdownRequest):
    return compute_drawdown_analysis(payload)


@app.post("/api/v1/portfolio/optimize")
async def portfolio_optimize(payload: OptimizeRequest):
    return await compute_portfolio_optimization(payload)


# Phase 13: Advanced Portfolio Analytics
@app.post("/api/v1/portfolio/kelly-allocation")
async def portfolio_kelly(payload: KellyRequest):
    return await compute_kelly_allocation(payload)


@app.post("/api/v1/portfolio/regime-sizing")
async def portfolio_regime(payload: RegimeSizingRequest):
    return await compute_regime_sizing(payload)


@app.post("/api/v1/portfolio/monte-carlo-var")
async def portfolio_monte_carlo(payload: MonteCarloRequest):
    return await compute_monte_carlo_var(payload)


@app.post("/api/v1/portfolio/risk-warning")
async def portfolio_vpin(payload: VPINRequest):
    return await compute_vpin(payload)


# Phase 7a: Swing detect public API
@app.post("/api/v1/indicators/swings", response_model=SwingDetectResponse)
def indicators_swings(payload: SwingDetectRequest) -> SwingDetectResponse:
    return calculate_swing_points(payload)


# Phase 7c: Enhanced Bollinger variants
@app.post("/api/v1/indicators/bollinger/bandwidth")
def indic_bb_bandwidth(payload: BollingerVariantRequest):
    return calculate_bb_bandwidth(payload)


@app.post("/api/v1/indicators/bollinger/percent-b")
def indic_bb_percent_b(payload: BollingerVariantRequest):
    return calculate_bb_percent_b(payload)


@app.post("/api/v1/indicators/bollinger/squeeze", response_model=BollingerSqueezeResponse)
def indic_bb_squeeze(payload: BollingerSqueezeRequest) -> BollingerSqueezeResponse:
    return calculate_bollinger_keltner_squeeze(payload)


@app.post("/api/v1/indicators/rsi/atr-adjusted")
def indic_rsi_atr(payload: RSIVariantRequest):
    return calculate_atr_rsi(payload)


@app.post("/api/v1/indicators/rsi/bollinger", response_model=BollingerOnRSIResponse)
def indic_rsi_bollinger(payload: BollingerVariantRequest) -> BollingerOnRSIResponse:
    return calculate_bollinger_on_rsi(payload)


@app.post("/api/v1/indicators/macd", response_model=MACDResponse)
def indic_macd(payload: MACDRequest) -> MACDResponse:
    return calculate_macd(payload)


@app.post("/api/v1/indicators/stochastic", response_model=StochasticResponse)
def indic_stochastic(payload: StochasticRequest) -> StochasticResponse:
    return calculate_stochastic(payload)


@app.post("/api/v1/indicators/adx", response_model=ADXResponse)
def indic_adx(payload: ADXRequest) -> ADXResponse:
    return calculate_adx(payload)


@app.post("/api/v1/indicators/hma", response_model=IndicatorResponse)
def indic_hma(payload: HMARequest) -> IndicatorResponse:
    return calculate_hma(payload)


@app.post("/api/v1/indicators/vwap", response_model=IndicatorResponse)
def indic_vwap(payload: VWAPRequest) -> IndicatorResponse:
    return calculate_vwap(payload)


@app.post("/api/v1/indicators/keltner", response_model=KeltnerResponse)
def indic_keltner(payload: KeltnerRequest) -> KeltnerResponse:
    return calculate_keltner(payload)


@app.post("/api/v1/indicators/ichimoku", response_model=IchimokuResponse)
def indic_ichimoku(payload: IchimokuRequest) -> IchimokuResponse:
    return calculate_ichimoku(payload)


# Phase 7d: Fibonacci confluence
@app.post("/api/v1/fibonacci/confluence", response_model=FibonacciConfluenceResponse)
async def fibonacci_confluence(payload: FibonacciConfluenceRequest) -> Any:
    ck = _body_key("fib-confluence", payload.model_dump())
    hit = await _cache().get(ck)
    if hit is not None:
        return JSONResponse(hit)
    result = build_fibonacci_confluence(payload)
    result_data = result.model_dump()
    await _cache().set(ck, result_data, ttl_seconds=TTL_INDICATOR)
    return JSONResponse(result_data)


# Phase 15b: Volatility Suite
@app.post("/api/v1/indicators/volatility-suite", response_model=VolatilitySuiteResponse)
def indicators_volatility_suite(payload: VolatilitySuiteRequest) -> VolatilitySuiteResponse:
    return calculate_volatility_suite(payload)


# Phase 15c: Regime Detection — 3 tiers
@app.post("/api/v1/regime/detect", response_model=RegimeDetectResponse)
def regime_detect(payload: RegimeDetectRequest) -> RegimeDetectResponse:
    return calculate_regime(payload)


@app.post("/api/v1/regime/markov", response_model=MarkovRegimeResponse)
def regime_markov(payload: RegimeDetectRequest) -> MarkovRegimeResponse:
    return calculate_markov_regime(payload)


@app.post("/api/v1/regime/hmm", response_model=HMMRegimeResponse)
def regime_hmm(payload: RegimeDetectRequest) -> HMMRegimeResponse:
    return calculate_hmm_regime(payload)


# Phase 15d: Alternative Bars + CUSUM
@app.post("/api/v1/indicators/alternative-bars", response_model=AlternativeBarsResponse)
def indicators_alternative_bars(payload: AlternativeBarsRequest) -> AlternativeBarsResponse:
    return calculate_alternative_bars(payload)


@app.post("/api/v1/indicators/cusum", response_model=CUSUMResponse)
def indicators_cusum(payload: CUSUMRequest) -> CUSUMResponse:
    return calculate_cusum(payload)


# Phase 15e: Mean-Reversion vs Momentum
@app.post("/api/v1/regime/meanrev-momentum", response_model=MeanRevMomentumResponse)
def regime_meanrev_momentum(payload: MeanRevMomentumRequest) -> MeanRevMomentumResponse:
    return calculate_meanrev_momentum(payload)


# Phase 15f: Performance Metrics
@app.post("/api/v1/eval/performance-metrics", response_model=PerformanceMetricsResponse)
def eval_performance_metrics(payload: PerformanceMetricsRequest) -> PerformanceMetricsResponse:
    return calculate_performance_metrics(payload)


# Phase 15g: Signal Chain + Order Flow State Machine
@app.post("/api/v1/signals/quality-chain", response_model=SignalQualityChainResponse)
def signals_quality_chain(payload: SignalQualityChainRequest) -> SignalQualityChainResponse:
    return calculate_signal_quality_chain(payload)


@app.post("/api/v1/orderflow/state-machine", response_model=OrderFlowStateResponse)
def orderflow_state_machine(payload: OrderFlowStateRequest) -> OrderFlowStateResponse:
    return calculate_order_flow_state(payload)


# Phase 15h: Eval Baseline
@app.post("/api/v1/eval/baseline", response_model=EvalBaselineResponse)
def eval_baseline(payload: EvalBaselineRequest) -> EvalBaselineResponse:
    return calculate_eval_baseline(payload)


# Phase 16: Backtesting + Eval Hardening
@app.post("/api/v1/backtest/run", response_model=BacktestResponse)
def backtest_run(payload: BacktestRequest) -> BacktestResponse:
    return run_backtest(payload)


@app.post("/api/v1/backtest/walk-forward", response_model=WalkForwardResponse)
def backtest_walk_forward(payload: WalkForwardRequest) -> WalkForwardResponse:
    return run_walk_forward(payload)


@app.post("/api/v1/backtest/triple-barrier", response_model=TripleBarrierResponse)
def backtest_triple_barrier(payload: TripleBarrierRequest) -> TripleBarrierResponse:
    return calculate_triple_barrier(payload)


@app.post("/api/v1/backtest/parameter-sensitivity", response_model=ParameterSensitivityResponse)
def backtest_parameter_sensitivity(payload: ParameterSensitivityRequest) -> ParameterSensitivityResponse:
    return run_parameter_sensitivity(payload)


@app.post("/api/v1/eval/deflated-sharpe", response_model=DeflatedSharpeResponse)
def eval_deflated_sharpe(payload: DeflatedSharpeRequest) -> DeflatedSharpeResponse:
    return calculate_deflated_sharpe(payload)


@app.post("/api/v1/eval/indicator", response_model=EvalIndicatorResponse)
def eval_indicator(payload: EvalIndicatorRequest) -> EvalIndicatorResponse:
    return evaluate_indicator(payload)


# Phase 20: ML Pipeline
@app.post("/api/v1/ml/feature-engineering", response_model=FeatureEngineeringResponse)
def ml_feature_engineering(payload: FeatureEngineeringRequest) -> FeatureEngineeringResponse:
    return build_features(payload)


@app.post("/api/v1/ml/classify-signal", response_model=MLClassifySignalResponse)
def ml_classify_signal(payload: MLClassifySignalRequest) -> MLClassifySignalResponse:
    return classify_signal(payload)


@app.post("/api/v1/ml/hybrid-fusion", response_model=HybridFusionResponse)
def ml_hybrid_fusion(payload: HybridFusionRequest) -> HybridFusionResponse:
    return fuse_hybrid(payload)


@app.post("/api/v1/ml/bias-monitoring", response_model=BiasMonitoringResponse)
def ml_bias_monitoring(payload: BiasMonitoringRequest) -> BiasMonitoringResponse:
    return monitor_bias(payload)


# Phase 18: Options + Dark Pool + DeFi + Oracle Cross-Check
@app.post("/api/v1/darkpool/signal", response_model=DarkPoolSignalResponse)
def darkpool_signal(payload: DarkPoolSignalRequest) -> DarkPoolSignalResponse:
    return calculate_dark_pool_signal(payload)


@app.post("/api/v1/options/gex-profile", response_model=GEXProfileResponse)
def options_gex_profile(payload: GEXProfileRequest) -> GEXProfileResponse:
    return calculate_gex_profile(payload)


@app.post("/api/v1/options/expected-move", response_model=ExpectedMoveResponse)
def options_expected_move(payload: ExpectedMoveRequest) -> ExpectedMoveResponse:
    return calculate_expected_move(payload)


@app.post("/api/v1/options/calculator", response_model=OptionsCalculatorResponse)
def options_calculator(payload: OptionsCalculatorRequest) -> OptionsCalculatorResponse:
    return calculate_options_payoff(payload)


@app.post("/api/v1/defi/stress", response_model=DeFiStressResponse)
def defi_stress(payload: DeFiStressRequest) -> DeFiStressResponse:
    return calculate_defi_stress(payload)


@app.post("/api/v1/oracle/cross-check", response_model=OracleCrossCheckResponse)
def oracle_cross_check(payload: OracleCrossCheckRequest) -> OracleCrossCheckResponse:
    return calculate_oracle_crosscheck(payload)


# ---------------------------------------------------------------------------
# Rainbow Collection (Kaabar 2026, Ch. 3/7/10)
# ---------------------------------------------------------------------------


@app.post("/api/v1/rainbow/collection", response_model=RainbowResponse)
def rainbow_collection(payload: RainbowRequest) -> RainbowResponse:
    return calculate_rainbow_collection(payload)


@app.post("/api/v1/rainbow/composite", response_model=IndicatorResponse)
def rainbow_composite(payload: RainbowRequest) -> IndicatorResponse:
    return rainbow_composite_score(payload)


@app.post("/api/v1/patterns/r-pattern", response_model=RPatternResponse)
def r_pattern(payload: RPatternRequest) -> RPatternResponse:
    return calculate_r_pattern(payload)


@app.post("/api/v1/patterns/gap-pattern", response_model=GapPatternResponse)
def gap_pattern(payload: GapPatternRequest) -> GapPatternResponse:
    return calculate_gap_pattern(payload)


# ---------------------------------------------------------------------------
# Rob Booker Reversal (Kaabar 2026, Ch. 12)
# ---------------------------------------------------------------------------


@app.post("/api/v1/indicators/rob-booker-reversal", response_model=IndicatorResponse)
def rob_booker_reversal(payload: RobBookerReversalRequest) -> IndicatorResponse:
    return calculate_rob_booker_reversal(payload)


# ---------------------------------------------------------------------------
# Cross-Asset RSI Convergence (Kaabar 2026, Ch. 6)
# ---------------------------------------------------------------------------


@app.post("/api/v1/indicators/cross-asset-convergence", response_model=CrossAssetConvergenceResponse)
def cross_asset_convergence(payload: CrossAssetConvergenceRequest) -> CrossAssetConvergenceResponse:
    return calculate_cross_asset_convergence(payload)


# ---------------------------------------------------------------------------
# Swarming — Multi-Chart-System Validation (Kaabar 2026, Kap. 4/9/11)
# ---------------------------------------------------------------------------


@app.post("/api/v1/patterns/swarm-validate", response_model=SwarmValidationResponse)
def swarm_validate_endpoint(payload: SwarmValidationRequest) -> SwarmValidationResponse:
    return swarm_validate(
        ohlcv=payload.ohlcv,
        pattern_fn=payload.pattern_type,
        lookback=payload.lookback,
        threshold=payload.threshold,
    )


# ---------------------------------------------------------------------------
# Regime-Weighted Patterns (Kaabar 2026, Ch. 1)
# ---------------------------------------------------------------------------


@app.post("/api/v1/patterns/regime-weighted", response_model=PatternResponse)
def regime_weighted_patterns(payload: PatternRequest) -> PatternResponse:
    """Run pattern detection + apply regime-aware confidence weighting."""
    from .helpers import closes as extract_closes
    result = build_candlestick_patterns(payload)
    c = extract_closes(payload.ohlcv[-payload.lookback:])
    return regime_weight_patterns(result, c)


# ---------------------------------------------------------------------------
# RSI Signal Techniques (Kaabar 2026, Ch. 3)
# ---------------------------------------------------------------------------


@app.post("/api/v1/indicators/rsi-v-technique", response_model=IndicatorResponse)
def rsi_v_technique(payload: RSIVTechniqueRequest) -> IndicatorResponse:
    return calculate_rsi_v_technique(payload)


@app.post("/api/v1/indicators/rsi-dcc", response_model=IndicatorResponse)
def rsi_dcc(payload: RSIDCCRequest) -> IndicatorResponse:
    return calculate_rsi_dcc(payload)


@app.post("/api/v1/indicators/rsi-ma-cross", response_model=IndicatorResponse)
def rsi_ma_cross(payload: RSIMACrossRequest) -> IndicatorResponse:
    return calculate_rsi_ma_cross(payload)


# ---------------------------------------------------------------------------
# BB Signal Techniques (Kaabar 2026, Ch. 3)
# ---------------------------------------------------------------------------


@app.post("/api/v1/indicators/bb-conservative", response_model=IndicatorResponse)
def bb_conservative(payload: BollingerVariantRequest) -> IndicatorResponse:
    return calculate_bb_conservative(payload)


@app.post("/api/v1/indicators/bb-aggressive", response_model=IndicatorResponse)
def bb_aggressive(payload: BollingerVariantRequest) -> IndicatorResponse:
    return calculate_bb_aggressive(payload)


@app.post("/api/v1/indicators/bb-trend-friendly", response_model=IndicatorResponse)
def bb_trend_friendly(payload: BBTrendFriendlyRequest) -> IndicatorResponse:
    return calculate_bb_trend_friendly(payload)


# ---------------------------------------------------------------------------
# WMA/IWMA Cross (Kaabar 2026, Ch. 3)
# ---------------------------------------------------------------------------


@app.post("/api/v1/indicators/wma-iwma-cross", response_model=IndicatorResponse)
def wma_iwma_cross(payload: WMAIWMACrossRequest) -> IndicatorResponse:
    return calculate_wma_iwma_cross(payload)


# ---------------------------------------------------------------------------
# Rainbow Confluence (Kaabar 2026, Ch. 3)
# ---------------------------------------------------------------------------


@app.post("/api/v1/rainbow/confluence", response_model=IndicatorResponse)
def rainbow_confluence(payload: RainbowRequest) -> IndicatorResponse:
    return calculate_rainbow_confluence(payload)
