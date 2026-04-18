"""Tests for agent.resilience.rate_limit_tracker (Ralph Phase 3 port).

Enterprise adaptations being tested:
- :func:`capture_from_response` takes ``user_id`` + ``provider_key_id`` so
  each caller's usage is tracked separately.
- :class:`RateLimitRegistry` stores buckets keyed on
  ``(user_id, provider_key_id, window)`` — in-memory only (Prometheus
  persistence lives elsewhere, per exec-17).
- :meth:`RateLimitBucket.to_prometheus_dict` returns labels fit for
  OpenObserve / Prometheus scrape.
- LiteLLM response shape (headers live under
  ``response._hidden_params["additional_headers"]``) is handled in the
  extraction path.
"""
from __future__ import annotations

from types import SimpleNamespace

from agent.resilience.rate_limit_tracker import (
    RateLimitBucket,
    RateLimitRegistry,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FULL_HEADERS_NOUS = {
    # requests per minute
    "x-ratelimit-limit-requests": "100",
    "x-ratelimit-remaining-requests": "25",
    "x-ratelimit-reset-requests": "30",
    # requests per hour
    "x-ratelimit-limit-requests-1h": "10000",
    "x-ratelimit-remaining-requests-1h": "9000",
    "x-ratelimit-reset-requests-1h": "3600",
    # tokens per minute
    "x-ratelimit-limit-tokens": "10000",
    "x-ratelimit-remaining-tokens": "2500",
    "x-ratelimit-reset-tokens": "60",
    # tokens per hour
    "x-ratelimit-limit-tokens-1h": "1000000",
    "x-ratelimit-remaining-tokens-1h": "500000",
    "x-ratelimit-reset-tokens-1h": "3600",
}


def _litellm_response(headers: dict) -> SimpleNamespace:
    """Fake a LiteLLM response object (headers under _hidden_params)."""
    return SimpleNamespace(_hidden_params={"additional_headers": headers})


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

def test_parse_all_12_headers():
    """Full Nous/OpenRouter 12-header set → all 4 windows populated."""
    registry = RateLimitRegistry()
    response = _litellm_response(FULL_HEADERS_NOUS)

    buckets = registry.capture_from_response(
        response, user_id="u1", provider_key_id="k1", provider="nous"
    )

    # capture returns exactly one bucket per window — 4 windows total.
    windows = {b.window for b in buckets}
    assert windows == {"requests", "requests-1h", "tokens", "tokens-1h"}, (
        f"expected all 4 windows, got {windows}"
    )

    # All four buckets must have non-zero limits (populated from headers).
    for b in buckets:
        assert b.limit > 0, f"bucket {b.window} has limit={b.limit}"

    # Spot-check one bucket's fields came from the correct header set.
    rpm = registry.get("u1", "k1", "requests")
    assert rpm is not None
    assert rpm.limit == 100
    assert rpm.remaining == 25
    assert rpm.reset_seconds == 30.0
    assert rpm.provider == "nous"


def test_litellm_hidden_params_shape():
    """LiteLLM hides headers under response._hidden_params["additional_headers"].

    The parser must read from that location, not from ``response.headers`` or
    kwargs.
    """
    headers = {
        "x-ratelimit-limit-requests": "200",
        "x-ratelimit-remaining-requests": "180",
        "x-ratelimit-reset-requests": "42",
    }
    response = _litellm_response(headers)

    registry = RateLimitRegistry()
    registry.capture_from_response(
        response, user_id="u1", provider_key_id="k1", provider="openrouter"
    )

    bucket = registry.get("u1", "k1", "requests")
    assert bucket is not None, (
        "parser failed to read headers from response._hidden_params"
    )
    assert bucket.limit == 200
    assert bucket.remaining == 180
    assert bucket.reset_seconds == 42.0


def test_missing_headers_yields_empty_bucket():
    """Response with no rate-limit headers → registry still holds a bucket
    with limit=0 (enterprise contract from plan §5 Phase 3)."""
    response = _litellm_response({})

    registry = RateLimitRegistry()
    buckets = registry.capture_from_response(
        response, user_id="u1", provider_key_id="k1"
    )

    # All 4 windows created even if empty.
    assert len(buckets) == 4
    for b in buckets:
        assert b.limit == 0
        assert b.remaining == 0
        assert b.reset_seconds == 0.0


# ---------------------------------------------------------------------------
# Bucket math
# ---------------------------------------------------------------------------

def test_bucket_properties_used_and_pct():
    """limit=1000, remaining=250 → used=750, usage_pct=75.0"""
    bucket = RateLimitBucket(limit=1000, remaining=250)
    assert bucket.used == 750
    assert bucket.usage_pct == 75.0


def test_bucket_zero_limit_is_safe():
    bucket = RateLimitBucket(limit=0, remaining=0)
    assert bucket.used == 0
    assert bucket.usage_pct == 0.0


# ---------------------------------------------------------------------------
# Registry semantics
# ---------------------------------------------------------------------------

def test_registry_separates_users():
    """Same provider_key but different user_id → separate buckets."""
    headers_alice = {
        "x-ratelimit-limit-requests": "100",
        "x-ratelimit-remaining-requests": "90",
        "x-ratelimit-reset-requests": "30",
    }
    headers_bob = {
        "x-ratelimit-limit-requests": "100",
        "x-ratelimit-remaining-requests": "42",
        "x-ratelimit-reset-requests": "30",
    }

    registry = RateLimitRegistry()
    registry.capture_from_response(
        _litellm_response(headers_alice),
        user_id="alice",
        provider_key_id="shared-key-1",
        provider="nous",
    )
    registry.capture_from_response(
        _litellm_response(headers_bob),
        user_id="bob",
        provider_key_id="shared-key-1",
        provider="nous",
    )

    alice = registry.get("alice", "shared-key-1", "requests")
    bob = registry.get("bob", "shared-key-1", "requests")

    assert alice is not None and bob is not None
    assert alice.remaining == 90
    assert bob.remaining == 42
    assert alice is not bob, "registry must not collapse different users"


def test_registry_overwrites_same_key():
    """Re-capturing for same (user, key, window) updates the bucket."""
    headers_v1 = {
        "x-ratelimit-limit-requests": "100",
        "x-ratelimit-remaining-requests": "80",
    }
    headers_v2 = {
        "x-ratelimit-limit-requests": "100",
        "x-ratelimit-remaining-requests": "70",
    }

    registry = RateLimitRegistry()
    registry.capture_from_response(
        _litellm_response(headers_v1), user_id="u1", provider_key_id="k1"
    )
    registry.capture_from_response(
        _litellm_response(headers_v2), user_id="u1", provider_key_id="k1"
    )

    bucket = registry.get("u1", "k1", "requests")
    assert bucket is not None
    assert bucket.remaining == 70


# ---------------------------------------------------------------------------
# Prometheus export
# ---------------------------------------------------------------------------

def test_to_prometheus_dict_has_labels():
    """Bucket's prometheus dict must include user_id, provider, window labels."""
    bucket = RateLimitBucket(
        limit=100,
        remaining=25,
        reset_seconds=30.0,
        window="requests",
        user_id="alice",
        provider="nous",
        provider_key_id="k1",
    )
    export = bucket.to_prometheus_dict()

    # The plan mandates these label keys — callers will build Prom metric
    # names from them. If the location moves (labels vs top-level), that's
    # fine as long as the keys exist somewhere accessible.
    flat = dict(export.get("labels", {}))
    for required in ("user_id", "provider", "window"):
        assert required in flat, (
            f"prometheus dict missing required label {required!r}; got keys {sorted(flat.keys())}"
        )
    assert flat["user_id"] == "alice"
    assert flat["provider"] == "nous"
    assert flat["window"] == "requests"

    # And the numeric metrics must be exposed.
    metrics = export.get("metrics", {})
    assert "limit" in metrics and "remaining" in metrics
    assert metrics["limit"] == 100
    assert metrics["remaining"] == 25


# ---------------------------------------------------------------------------
# Review-driven pinning tests
# ---------------------------------------------------------------------------

def test_remaining_seconds_now_respects_captured_at_zero():
    """Regression (review M-2): when captured_at==0 the bucket is unpopulated
    and remaining_seconds_now must return the raw reset_seconds — no
    decay — so callers don't see phantom negatives from the epoch."""
    bucket = RateLimitBucket(limit=0, remaining=0, reset_seconds=30.0, captured_at=0.0)
    assert bucket.remaining_seconds_now == 30.0


def test_remaining_seconds_now_decays_when_captured():
    """When a bucket was captured in the recent past, the remaining seconds
    must decay linearly."""
    import time

    bucket = RateLimitBucket(
        limit=100, remaining=10, reset_seconds=30.0, captured_at=time.time() - 5,
    )
    # 5s of the original 30s have elapsed → roughly 25s remain.
    assert 23.0 <= bucket.remaining_seconds_now <= 27.0
