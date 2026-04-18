"""Tests for agent.resilience.error_classifier (Ralph Phase 2 port).

Enterprise adaptations being tested:
- Errors come from ``litellm.exceptions`` (matrix gateway is LiteLLM), not
  provider-SDK classes.
- :class:`FailoverReason` includes the matrix-specific ``upstream_unavailable``
  (LiteLLM fallback-chain exhausted).
- :func:`classify_error` is **pure** — callers get a :class:`ClassificationResult`
  with a :class:`RecoveryStrategy` hint; no logging, no side-effects.
- Priority-dispatch: ``auth → billing → rate_limit → context_overflow →
  overloaded → server_error → timeout → format_error → unknown``.
"""
from __future__ import annotations

from litellm.exceptions import (
    AuthenticationError,
    BadRequestError,
    BudgetExceededError,
    ContextWindowExceededError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from agent.resilience.error_classifier import (
    ClassificationResult,
    FailoverReason,
    RecoveryStrategy,
    classify_error,
)


def _make(cls, message: str, **kwargs):
    """Minimal litellm-exception constructor for tests."""
    kwargs.setdefault("model", "gpt-4o-mini")
    kwargs.setdefault("llm_provider", "openai")
    return cls(message=message, **kwargs)


# ---------------------------------------------------------------------------
# One test per FailoverReason enum member
# ---------------------------------------------------------------------------

def test_classify_auth():
    """AuthenticationError → auth."""
    result = classify_error(_make(AuthenticationError, "invalid api key"))
    assert result.reason is FailoverReason.auth
    assert isinstance(result, ClassificationResult)


def test_classify_billing():
    """BudgetExceededError → billing (LiteLLM budget cap hit)."""
    exc = BudgetExceededError(
        current_cost=100.0, max_budget=50.0, message="budget exhausted"
    )
    result = classify_error(exc)
    assert result.reason is FailoverReason.billing


def test_classify_rate_limit():
    """RateLimitError → rate_limit."""
    result = classify_error(_make(RateLimitError, "rate limit exceeded"))
    assert result.reason is FailoverReason.rate_limit


def test_classify_context_overflow():
    """ContextWindowExceededError → context_overflow."""
    result = classify_error(
        _make(ContextWindowExceededError, "prompt is too long")
    )
    assert result.reason is FailoverReason.context_overflow


def test_classify_overloaded():
    """ServiceUnavailableError (503/529) → overloaded."""
    result = classify_error(
        _make(ServiceUnavailableError, "service temporarily unavailable")
    )
    assert result.reason is FailoverReason.overloaded


def test_classify_server_error():
    """InternalServerError (500/502) → server_error."""
    result = classify_error(_make(InternalServerError, "internal server error"))
    assert result.reason is FailoverReason.server_error


def test_classify_timeout():
    """Timeout (408) → timeout."""
    result = classify_error(_make(Timeout, "connection timed out"))
    assert result.reason is FailoverReason.timeout


def test_classify_format_error():
    """BadRequestError (400, NOT context-overflow) → format_error."""
    # A generic 400 with nothing context-related in the message.
    result = classify_error(
        _make(BadRequestError, "tool_choice must be one of auto/none/required")
    )
    assert result.reason is FailoverReason.format_error


def test_classify_upstream_unavailable():
    """Matrix-specific: LiteLLM fallback-chain exhausted → upstream_unavailable.

    The classifier must recognise the marker used when LiteLLM raises after
    every provider in its fallback list has failed.
    """
    result = classify_error(
        Exception("all fallback providers have been exhausted")
    )
    assert result.reason is FailoverReason.upstream_unavailable


def test_classify_unknown_classifiable():
    """A plain Exception with no recognisable pattern → unknown."""
    result = classify_error(Exception("something entirely novel happened"))
    assert result.reason is FailoverReason.unknown


def test_classify_truly_unknown_exception():
    """A custom Exception subclass the classifier has never seen → unknown."""
    class MatrixSideQuestError(Exception):
        pass

    result = classify_error(MatrixSideQuestError("???"))
    assert result.reason is FailoverReason.unknown


# ---------------------------------------------------------------------------
# Priority dispatch
# ---------------------------------------------------------------------------

def test_priority_context_overflow_beats_format_error():
    """ContextWindowExceededError inherits from BadRequestError (status 400).

    Despite matching both categories by type/status, priority order mandates
    ``context_overflow`` wins over ``format_error``.
    """
    exc = _make(ContextWindowExceededError, "prompt is too long")
    # Sanity: it *is* a BadRequestError shape (400-coded).
    assert isinstance(exc, BadRequestError)
    assert exc.status_code == 400

    result = classify_error(exc)
    assert result.reason is FailoverReason.context_overflow, (
        f"priority violated: expected context_overflow, got {result.reason}"
    )


# ---------------------------------------------------------------------------
# Recovery strategy dispatch
# ---------------------------------------------------------------------------

def test_recovery_strategy_rate_limit_says_backoff_then_rotate():
    result = classify_error(_make(RateLimitError, "too many requests"))
    assert result.recovery is RecoveryStrategy.backoff_then_rotate, (
        "rate_limit must map to backoff_then_rotate; "
        f"got {result.recovery}"
    )


def test_recovery_strategy_billing_says_rotate_immediately():
    exc = BudgetExceededError(
        current_cost=100.0, max_budget=50.0, message="budget exhausted"
    )
    result = classify_error(exc)
    assert result.recovery is RecoveryStrategy.rotate_immediately, (
        "billing must map to rotate_immediately; "
        f"got {result.recovery}"
    )


# ---------------------------------------------------------------------------
# Purity: classify_error has no side-effects
# ---------------------------------------------------------------------------

def test_classify_error_is_pure_no_logging(caplog):
    """The plan requires classify_error to be pure — no logging."""
    import logging

    with caplog.at_level(logging.DEBUG):
        classify_error(_make(RateLimitError, "rate limit"))
        classify_error(Exception("unknown"))
        classify_error(_make(AuthenticationError, "invalid key"))
    assert caplog.records == [], (
        f"classify_error emitted log records: {[r.getMessage() for r in caplog.records]}"
    )


# ---------------------------------------------------------------------------
# Review-driven pinning tests
# ---------------------------------------------------------------------------

def test_classify_rejects_non_exception():
    """Regression (review I-3): passing None / non-exception used to silently
    classify as unknown. Must raise TypeError so call-site bugs surface."""
    import pytest

    with pytest.raises(TypeError, match="expected BaseException"):
        classify_error(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="expected BaseException"):
        classify_error("not an exception")  # type: ignore[arg-type]


def test_classify_handles_stringified_status_code():
    """Regression (review I-3): some providers surface status_code as a
    numeric string (from JSON bodies). The walker must parse it."""
    class _FakeProviderError(Exception):
        status_code = "429"

    result = classify_error(_FakeProviderError("provider said 429"))
    assert result.reason is FailoverReason.rate_limit
    assert result.status_code == 429


def test_auth_message_defers_to_billing_match():
    """Pinning (review I-2): the auth-by-message check runs AFTER billing
    patterns. A message containing both markers must classify as billing —
    the more actionable recovery. Primary auth (isinstance / 401 / 403) is
    still first-priority."""
    exc = Exception("invalid api key: payment required")
    result = classify_error(exc)
    assert result.reason is FailoverReason.billing, (
        "auth-by-message must defer to billing-pattern match; "
        f"got {result.reason}"
    )

    # Primary auth path stays first-priority: a 401 still wins.
    class _Auth401Error(Exception):
        status_code = 401

    result_401 = classify_error(_Auth401Error("irrelevant message"))
    assert result_401.reason is FailoverReason.auth
