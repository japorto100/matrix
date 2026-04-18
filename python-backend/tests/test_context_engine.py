"""Tests for context.context_engine — exec-hermes §3.1 / exec-context §6.1."""
from __future__ import annotations

import pytest

from context.context_engine import (
    ContextEngine,
    ContextEngineConfig,
    ContextStage,
    DefaultContextEngine,
)

# ---------------------------------------------------------------------------
# ContextEngineConfig — threshold validation
# ---------------------------------------------------------------------------

def test_default_config_values():
    cfg = ContextEngineConfig()
    assert cfg.pre_save == 0.80
    assert cfg.compaction == 0.85
    assert cfg.emergency == 0.95


def test_custom_config_accepts_valid_ordering():
    cfg = ContextEngineConfig(pre_save=0.70, compaction=0.80, emergency=0.90)
    assert cfg.pre_save == 0.70


def test_config_rejects_reversed_thresholds():
    with pytest.raises(ValueError, match="must be"):
        ContextEngineConfig(pre_save=0.9, compaction=0.8, emergency=0.95)


def test_config_rejects_zero_or_one_thresholds():
    with pytest.raises(ValueError):
        ContextEngineConfig(pre_save=0.0, compaction=0.5, emergency=0.9)
    with pytest.raises(ValueError):
        ContextEngineConfig(pre_save=0.5, compaction=0.9, emergency=1.0)


# ---------------------------------------------------------------------------
# DefaultContextEngine — stage classification
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> DefaultContextEngine:
    return DefaultContextEngine()


def test_stage_normal_below_pre_save(engine):
    assert engine.stage_for(tokens=50_000, window=200_000) is ContextStage.normal
    # Exactly 79% is still normal.
    assert engine.stage_for(tokens=158_000, window=200_000) is ContextStage.normal


def test_stage_pre_save_at_threshold(engine):
    # 80% exactly → pre_save
    assert engine.stage_for(tokens=160_000, window=200_000) is ContextStage.pre_save
    # 84% still pre_save
    assert engine.stage_for(tokens=168_000, window=200_000) is ContextStage.pre_save


def test_stage_compaction_at_threshold(engine):
    # 85% exactly → compaction
    assert engine.stage_for(tokens=170_000, window=200_000) is ContextStage.compaction
    # 94% still compaction
    assert engine.stage_for(tokens=188_000, window=200_000) is ContextStage.compaction


def test_stage_emergency_at_threshold(engine):
    # 95% exactly → emergency
    assert engine.stage_for(tokens=190_000, window=200_000) is ContextStage.emergency
    # 99% still emergency
    assert engine.stage_for(tokens=198_000, window=200_000) is ContextStage.emergency


def test_stage_normal_when_window_unknown(engine):
    """window <= 0 (unknown model) must yield normal — caller can't compare."""
    assert engine.stage_for(tokens=100_000, window=0) is ContextStage.normal
    assert engine.stage_for(tokens=100_000, window=-1) is ContextStage.normal


def test_stage_normal_when_negative_tokens(engine):
    assert engine.stage_for(tokens=-100, window=200_000) is ContextStage.normal


# ---------------------------------------------------------------------------
# DefaultContextEngine — predicate helpers
# ---------------------------------------------------------------------------

def test_should_verbatim_retain_at_pre_save(engine):
    assert engine.should_verbatim_retain(tokens=160_000, window=200_000) is True


def test_should_verbatim_retain_below_pre_save(engine):
    assert engine.should_verbatim_retain(tokens=100_000, window=200_000) is False


def test_should_compact_only_at_compaction_or_above(engine):
    # pre_save alone does not trigger compaction
    assert engine.should_compact(tokens=160_000, window=200_000) is False
    # compaction stage
    assert engine.should_compact(tokens=170_000, window=200_000) is True
    # emergency also implies compaction
    assert engine.should_compact(tokens=190_000, window=200_000) is True


def test_should_emergency_compact_only_at_emergency(engine):
    assert engine.should_emergency_compact(tokens=170_000, window=200_000) is False
    assert engine.should_emergency_compact(tokens=190_000, window=200_000) is True


def test_transition_ordering_invariant():
    """For any fill ratio, verbatim ⊇ compact ⊇ emergency (implication chain)."""
    engine = DefaultContextEngine()
    for tokens in range(0, 200_000, 5_000):
        v = engine.should_verbatim_retain(tokens=tokens, window=200_000)
        c = engine.should_compact(tokens=tokens, window=200_000)
        e = engine.should_emergency_compact(tokens=tokens, window=200_000)
        # Each higher predicate must imply the lower.
        if c:
            assert v, f"tokens={tokens}: compact without verbatim_retain"
        if e:
            assert c, f"tokens={tokens}: emergency without compact"


# ---------------------------------------------------------------------------
# Custom config override
# ---------------------------------------------------------------------------

def test_custom_thresholds_respected():
    """A per-model override config changes the thresholds."""
    # Shift pre_save down to 60% — useful for short-context models
    cfg = ContextEngineConfig(pre_save=0.60, compaction=0.75, emergency=0.90)
    engine = DefaultContextEngine(cfg)

    # 65% of 10k tokens → pre_save (normal under default 80% threshold)
    assert engine.stage_for(tokens=6_500, window=10_000) is ContextStage.pre_save
    # 80% → compaction under custom (vs pre_save under default)
    assert engine.stage_for(tokens=8_000, window=10_000) is ContextStage.compaction


# ---------------------------------------------------------------------------
# ABC enforcement — cannot instantiate abstract class
# ---------------------------------------------------------------------------

def test_context_engine_is_abstract():
    with pytest.raises(TypeError):
        ContextEngine()  # type: ignore[abstract]


def test_subclass_must_implement_stage_for():
    class BrokenEngine(ContextEngine):
        pass

    with pytest.raises(TypeError):
        BrokenEngine()  # type: ignore[abstract]
