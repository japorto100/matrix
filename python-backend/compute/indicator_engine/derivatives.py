"""derivatives.py — Options, DeFi, dark pool, and market microstructure.

Extracted from pipeline.py (Phase A, 20.03.2026).

Functions:
  calculate_dark_pool_signal, calculate_gex_profile,
  calculate_expected_move, calculate_options_payoff,
  calculate_defi_stress, calculate_oracle_crosscheck
"""

from __future__ import annotations

import math as _math
from typing import Literal

from indicator_engine.models import (
    DarkPoolSignalRequest,
    DarkPoolSignalResponse,
    DeFiStressRequest,
    DeFiStressResponse,
    ExpectedMoveRequest,
    ExpectedMoveResponse,
    GEXProfileRequest,
    GEXProfileResponse,
    OptionsCalculatorRequest,
    OptionsCalculatorResponse,
    OracleCrossCheckRequest,
    OracleCrossCheckResponse,
)


def calculate_dark_pool_signal(req: DarkPoolSignalRequest) -> DarkPoolSignalResponse:
    """Dark pool activity signal — accumulation/distribution based on DP ratio."""
    total = req.lit_volume + req.dark_pool_volume
    ratio = req.dark_pool_volume / total if total > 0 else 0.0
    if ratio > 0.45:
        signal: Literal["accumulation", "distribution", "neutral"] = "accumulation"
    elif ratio < 0.15:
        signal = "distribution"
    else:
        signal = "neutral"
    conf = min(1.0, abs(ratio - 0.30) / 0.30)
    return DarkPoolSignalResponse(dark_pool_ratio=round(ratio, 6), signal=signal, confidence=round(conf, 6))


def calculate_gex_profile(req: GEXProfileRequest) -> GEXProfileResponse:
    """Gamma Exposure profile — net GEX, call wall, put wall."""
    n = min(len(req.strikes), len(req.call_gamma), len(req.put_gamma))
    strikes = req.strikes[:n]
    net = [req.call_gamma[i] - req.put_gamma[i] for i in range(n)]
    call_idx = max(range(n), key=lambda i: req.call_gamma[i])
    put_idx = max(range(n), key=lambda i: req.put_gamma[i])
    return GEXProfileResponse(
        net_gex=[round(x, 6) for x in net],
        call_wall=round(strikes[call_idx], 6),
        put_wall=round(strikes[put_idx], 6),
    )


def calculate_expected_move(req: ExpectedMoveRequest) -> ExpectedMoveResponse:
    """Expected move from implied volatility and time horizon."""
    t = req.days / 365.0
    move = req.spot * req.iv_annual * _math.sqrt(t)
    return ExpectedMoveResponse(
        move_abs=round(move, 6),
        upper=round(req.spot + move, 6),
        lower=round(max(0.0, req.spot - move), 6),
    )


def calculate_options_payoff(req: OptionsCalculatorRequest) -> OptionsCalculatorResponse:
    """Options payoff calculator — max profit/loss and breakeven levels."""
    min_s = min(leg.strike for leg in req.legs) * 0.2
    max_s = max(leg.strike for leg in req.legs) * 2.0
    grid = [min_s + i * (max_s - min_s) / 200 for i in range(201)]
    payoffs: list[float] = []
    for s in grid:
        total = 0.0
        for leg in req.legs:
            if leg.kind == "call":
                intrinsic = max(0.0, s - leg.strike)
            else:
                intrinsic = max(0.0, leg.strike - s)
            total += (intrinsic - leg.premium) * leg.quantity * req.underlying_qty
        payoffs.append(total)
    max_profit = max(payoffs)
    max_loss = min(payoffs)
    breakevens: list[float] = []
    for i in range(1, len(grid)):
        if payoffs[i - 1] == 0:
            breakevens.append(grid[i - 1])
        elif payoffs[i] == 0 or (payoffs[i - 1] < 0 < payoffs[i]) or (payoffs[i - 1] > 0 > payoffs[i]):
            breakevens.append(grid[i])
    return OptionsCalculatorResponse(
        max_profit=round(max_profit, 6),
        max_loss=round(max_loss, 6),
        breakevens=[round(x, 6) for x in breakevens[:4]],
    )


def calculate_defi_stress(req: DeFiStressRequest) -> DeFiStressResponse:
    """DeFi stress index — TVL change + funding rate + OI change."""
    score = (
        0.4 * abs(req.tvl_change_pct)
        + 0.3 * abs(req.funding_rate) * 100.0
        + 0.3 * abs(req.open_interest_change_pct)
    )
    if score > 25:
        level: Literal["low", "medium", "high"] = "high"
    elif score > 10:
        level = "medium"
    else:
        level = "low"
    return DeFiStressResponse(stress_score=round(score, 6), level=level)


def calculate_oracle_crosscheck(req: OracleCrossCheckRequest) -> OracleCrossCheckResponse:
    """Oracle price divergence check — Web2 vs on-chain price."""
    div = abs(req.web2_price - req.oracle_price) / req.oracle_price
    disagreement = div > req.threshold_pct
    if div > req.threshold_pct * 3:
        sev: Literal["low", "medium", "high"] = "high"
    elif div > req.threshold_pct * 1.5:
        sev = "medium"
    else:
        sev = "low"
    return OracleCrossCheckResponse(
        divergence_pct=round(div, 6),
        disagreement=disagreement,
        severity=sev,
    )
