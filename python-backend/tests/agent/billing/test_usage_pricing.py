"""Tests for agent/billing/usage_pricing.py."""
from __future__ import annotations

from decimal import Decimal

from agent.billing.usage_pricing import (
    CanonicalUsage,
    estimate_usage_cost,
    usage_from_litellm,
)


def test_canonical_usage_defaults():
    u = CanonicalUsage()
    assert u.input_tokens == 0
    assert u.output_tokens == 0
    assert u.total_tokens == 0
    assert u.request_count == 1


def test_total_tokens_includes_cache():
    u = CanonicalUsage(
        input_tokens=100,
        output_tokens=50,
        cache_read_tokens=200,
        cache_write_tokens=75,
    )
    assert u.prompt_tokens == 375
    assert u.total_tokens == 425


def test_usage_from_litellm_openai_shape():
    u = usage_from_litellm({
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500,
        "prompt_tokens_details": {"cached_tokens": 200},
    })
    assert u.cache_read_tokens == 200
    assert u.input_tokens == 800  # fresh = prompt - cached
    assert u.output_tokens == 500


def test_usage_from_litellm_anthropic_shape():
    u = usage_from_litellm({
        "prompt_tokens": 1000,  # LiteLLM normalises this
        "completion_tokens": 300,
        "cache_read_input_tokens": 600,
        "cache_creation_input_tokens": 100,
    })
    assert u.cache_read_tokens == 600
    assert u.cache_write_tokens == 100
    assert u.input_tokens == 300  # 1000 - 600 cache_read - 100 cache_write


def test_usage_from_litellm_reasoning_tokens():
    u = usage_from_litellm({
        "prompt_tokens": 500,
        "completion_tokens": 800,
        "completion_tokens_details": {"reasoning_tokens": 300},
    })
    assert u.reasoning_tokens == 300


def test_usage_from_litellm_empty():
    assert usage_from_litellm(None) == CanonicalUsage()
    assert usage_from_litellm({}) == CanonicalUsage()


def test_estimate_cost_via_litellm():
    # gpt-4o is a well-known LiteLLM model; its pricing is stable enough
    # that this should always return a concrete cost.
    u = CanonicalUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    r = estimate_usage_cost("gpt-4o", u)
    assert r.amount_usd is not None
    assert r.amount_usd > Decimal("0")
    assert r.status == "estimated"
    assert r.source == "litellm"


def test_estimate_cost_snapshot_fallback():
    """When LiteLLM has no data, snapshot-pricing should kick in."""
    # Pretend LiteLLM returned None by mocking via unknown model-name in a
    # namespace-less form that LiteLLM ~won't match. But our snapshot has
    # claude-opus-4-7; use a prefix to route to snapshot path cleanly.
    # Strategy: patch _cost_from_litellm to force None.
    from agent.billing import usage_pricing as up

    original = up._cost_from_litellm
    up._cost_from_litellm = lambda m, u: None
    try:
        u = CanonicalUsage(input_tokens=1_000_000, output_tokens=500_000)
        r = estimate_usage_cost("claude-opus-4-7", u)
        assert r.amount_usd is not None
        assert r.source == "snapshot"
        # Sanity: 15 USD/M input × 1M + 75 USD/M output × 0.5M = 15 + 37.5 = 52.5
        assert r.amount_usd == Decimal("52.5")
    finally:
        up._cost_from_litellm = original


def test_estimate_cost_unknown_model():
    from agent.billing import usage_pricing as up

    original = up._cost_from_litellm
    up._cost_from_litellm = lambda m, u: None
    try:
        u = CanonicalUsage(input_tokens=100, output_tokens=50)
        r = estimate_usage_cost("totally-made-up-model-xyz", u)
        assert r.amount_usd is None
        assert r.status == "unknown"
        assert r.source == "none"
        assert r.is_known is False
    finally:
        up._cost_from_litellm = original


def test_estimate_cost_no_tokens():
    # Zero-token request should return zero cost, not None.
    u = CanonicalUsage(input_tokens=0, output_tokens=0)
    r = estimate_usage_cost("gpt-4o", u)
    assert r.amount_usd == Decimal("0")
