"""Tests for indicator_engine.derivatives — dark pool, GEX, expected move, options, DeFi."""

from __future__ import annotations

from indicator_engine.derivatives import (
    calculate_dark_pool_signal,
    calculate_defi_stress,
    calculate_expected_move,
    calculate_gex_profile,
    calculate_options_payoff,
    calculate_oracle_crosscheck,
)


class TestDarkPoolSignal:
    def test_accumulation(self) -> None:
        from indicator_engine.models import DarkPoolSignalRequest
        req = DarkPoolSignalRequest(lit_volume=5000, dark_pool_volume=6000)
        resp = calculate_dark_pool_signal(req)
        assert resp.signal == "accumulation"
        assert resp.dark_pool_ratio > 0.45

    def test_distribution(self) -> None:
        from indicator_engine.models import DarkPoolSignalRequest
        req = DarkPoolSignalRequest(lit_volume=9000, dark_pool_volume=500)
        resp = calculate_dark_pool_signal(req)
        assert resp.signal == "distribution"

    def test_neutral(self) -> None:
        from indicator_engine.models import DarkPoolSignalRequest
        req = DarkPoolSignalRequest(lit_volume=7000, dark_pool_volume=3000)
        resp = calculate_dark_pool_signal(req)
        assert resp.signal == "neutral"


class TestGEXProfile:
    def test_response(self) -> None:
        from indicator_engine.models import GEXProfileRequest
        req = GEXProfileRequest(
            strikes=[100.0, 110.0, 120.0],
            call_gamma=[0.5, 1.0, 0.3],
            put_gamma=[0.8, 0.2, 0.6],
        )
        resp = calculate_gex_profile(req)
        assert len(resp.net_gex) == 3
        assert resp.call_wall == 110.0  # max call gamma
        assert resp.put_wall == 100.0   # max put gamma


class TestExpectedMove:
    def test_basic(self) -> None:
        from indicator_engine.models import ExpectedMoveRequest
        req = ExpectedMoveRequest(spot=100.0, iv_annual=0.2, days=30)
        resp = calculate_expected_move(req)
        assert resp.upper > 100.0
        assert resp.lower < 100.0
        assert resp.move_abs > 0

    def test_zero_iv(self) -> None:
        from indicator_engine.models import ExpectedMoveRequest
        req = ExpectedMoveRequest(spot=100.0, iv_annual=0.0, days=30)
        resp = calculate_expected_move(req)
        assert resp.move_abs == 0.0
        assert resp.upper == 100.0
        assert resp.lower == 100.0


class TestOptionsPayoff:
    def test_long_call(self) -> None:
        from indicator_engine.models import OptionsCalculatorRequest, OptionLeg
        req = OptionsCalculatorRequest(
            spot=100.0,
            legs=[OptionLeg(kind="call", strike=100.0, premium=5.0)],
        )
        resp = calculate_options_payoff(req)
        assert resp.max_loss < 0  # limited loss (premium paid)
        assert resp.max_profit > 0

    def test_straddle(self) -> None:
        from indicator_engine.models import OptionsCalculatorRequest, OptionLeg
        req = OptionsCalculatorRequest(
            spot=100.0,
            legs=[
                OptionLeg(kind="call", strike=100.0, premium=5.0),
                OptionLeg(kind="put", strike=100.0, premium=5.0),
            ],
        )
        resp = calculate_options_payoff(req)
        assert resp.max_loss < 0
        assert len(resp.breakevens) >= 1


class TestDeFiStress:
    def test_high_stress(self) -> None:
        from indicator_engine.models import DeFiStressRequest
        req = DeFiStressRequest(tvl_change_pct=-50.0, funding_rate=0.5, open_interest_change_pct=30.0)
        resp = calculate_defi_stress(req)
        assert resp.level == "high"

    def test_low_stress(self) -> None:
        from indicator_engine.models import DeFiStressRequest
        req = DeFiStressRequest(tvl_change_pct=-1.0, funding_rate=0.01, open_interest_change_pct=2.0)
        resp = calculate_defi_stress(req)
        assert resp.level == "low"


class TestOracleCrossCheck:
    def test_agreement(self) -> None:
        from indicator_engine.models import OracleCrossCheckRequest
        req = OracleCrossCheckRequest(web2_price=100.0, oracle_price=100.05)
        resp = calculate_oracle_crosscheck(req)
        assert resp.disagreement is False

    def test_disagreement(self) -> None:
        from indicator_engine.models import OracleCrossCheckRequest
        req = OracleCrossCheckRequest(web2_price=100.0, oracle_price=95.0)
        resp = calculate_oracle_crosscheck(req)
        assert resp.disagreement is True
        assert resp.severity in ("low", "medium", "high")
