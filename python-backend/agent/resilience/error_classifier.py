"""LLM-API error classifier — structured failover taxonomy + recovery hints.

Enterprise port of ``_ref/hermes-agent/agent/error_classifier.py`` adapted
for the matrix LiteLLM-gateway harness:

- Pattern matches against ``litellm.exceptions`` types (matrix gateway is
  LiteLLM) instead of provider-specific SDK classes. Message/status-code
  fallbacks keep the classifier robust to exception shapes it has not seen.
- Adds the matrix-specific ``FailoverReason.upstream_unavailable`` for
  LiteLLM fallback-chain exhaustion.
- :func:`classify_error` is **pure**: it inspects the exception and returns
  a :class:`ClassificationResult`. No logging, no state, no I/O — callers
  compose retry / rotation / fallback policy on top.

Priority dispatch (plan §5 Phase 2):

    auth → billing → rate_limit → context_overflow → overloaded →
    server_error → timeout → format_error → unknown

``upstream_unavailable`` is probed just before ``unknown`` — it relies on
LiteLLM writing a specific marker message when every provider in the
fallback chain has been tried.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional

from litellm import exceptions as _lexc

__all__ = [
    "FailoverReason",
    "RecoveryStrategy",
    "ClassificationResult",
    "classify_error",
]


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------

class FailoverReason(enum.Enum):
    """Why an LLM-API call failed — drives recovery strategy dispatch."""

    auth = "auth"                              # 401/403, refresh or rotate
    billing = "billing"                        # 402, budget exhausted — rotate
    rate_limit = "rate_limit"                  # 429, backoff then rotate
    context_overflow = "context_overflow"      # context too big — compress
    overloaded = "overloaded"                  # 503/529, provider busy
    server_error = "server_error"              # 500/502, transient infra
    timeout = "timeout"                        # connection/read timeout
    format_error = "format_error"              # 400, malformed request
    upstream_unavailable = "upstream_unavailable"  # matrix: all fallbacks out
    unknown = "unknown"                        # fallback catch-all


class RecoveryStrategy(enum.Enum):
    """Canonical recovery action hint for the caller."""

    retry = "retry"                            # retry same provider
    backoff_then_retry = "backoff_then_retry"  # wait, then retry same provider
    backoff_then_rotate = "backoff_then_rotate"  # wait, then rotate credential
    rotate_immediately = "rotate_immediately"  # rotate credential now
    compress = "compress"                      # reduce context, then retry
    fallback = "fallback"                      # try next provider in the chain
    abort = "abort"                            # non-retryable, stop


@dataclass(frozen=True)
class ClassificationResult:
    """Structured classification of an API error."""

    reason: FailoverReason
    recovery: RecoveryStrategy
    status_code: Optional[int] = None
    message: str = ""
    retryable: bool = True


# ---------------------------------------------------------------------------
# Recovery strategy mapping (stable — callers depend on this)
# ---------------------------------------------------------------------------

_RECOVERY: dict[FailoverReason, RecoveryStrategy] = {
    FailoverReason.auth: RecoveryStrategy.rotate_immediately,
    FailoverReason.billing: RecoveryStrategy.rotate_immediately,
    FailoverReason.rate_limit: RecoveryStrategy.backoff_then_rotate,
    FailoverReason.context_overflow: RecoveryStrategy.compress,
    FailoverReason.overloaded: RecoveryStrategy.backoff_then_retry,
    FailoverReason.server_error: RecoveryStrategy.backoff_then_retry,
    FailoverReason.timeout: RecoveryStrategy.retry,
    FailoverReason.format_error: RecoveryStrategy.abort,
    FailoverReason.upstream_unavailable: RecoveryStrategy.fallback,
    FailoverReason.unknown: RecoveryStrategy.backoff_then_retry,
}

_NON_RETRYABLE: frozenset[FailoverReason] = frozenset({
    FailoverReason.format_error,
})


# ---------------------------------------------------------------------------
# Pattern tables (message-based fallback classification)
# ---------------------------------------------------------------------------

_AUTH_PATTERNS = (
    "invalid api key",
    "invalid_api_key",
    "authentication",
    "unauthorized",
    "forbidden",
    "access denied",
    "invalid token",
    "token expired",
    "token revoked",
)

_BILLING_PATTERNS = (
    "budget exhausted",
    "insufficient credits",
    "insufficient_quota",
    "credit balance",
    "credits have been exhausted",
    "payment required",
    "billing hard limit",
    "exceeded your current quota",
    "account is deactivated",
    "budget exceeded",
)

_RATE_LIMIT_PATTERNS = (
    "rate limit",
    "rate_limit",
    "too many requests",
    "throttled",
    "throttlingexception",
    "resource_exhausted",
    "requests per minute",
    "tokens per minute",
)

_CONTEXT_OVERFLOW_PATTERNS = (
    "context length",
    "context size",
    "context window",
    "maximum context",
    "token limit",
    "too many tokens",
    "prompt is too long",
    "prompt length",
    "max_tokens",
    "maximum number of tokens",
    "reduce the length",
    "exceeds the max_model_len",
    "input is too long",
    "context length exceeded",
)

_SERVER_ERROR_PATTERNS = (
    "internal server error",
    "bad gateway",
)

_OVERLOADED_PATTERNS = (
    "overloaded",
    "service unavailable",
    "service temporarily unavailable",
    "temporarily overloaded",
)

_TIMEOUT_PATTERNS = (
    "timed out",
    "timeout",
    "connection timeout",
    "read timeout",
)

_FORMAT_ERROR_PATTERNS = (
    "bad request",
    "invalid request",
    "validation error",
    "must be one of",
    "required",
)

_UPSTREAM_UNAVAILABLE_PATTERNS = (
    "all fallback providers",
    "fallback providers have been exhausted",
    "fallback chain exhausted",
    "no fallbacks available",
    "fallback exhausted",
)


def _any(msg: str, patterns: tuple[str, ...]) -> bool:
    return any(p in msg for p in patterns)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_error(exc: Exception) -> ClassificationResult:
    """Classify an exception raised by the LiteLLM gateway.

    Pure: no logging, no mutation, no I/O. Returns a
    :class:`ClassificationResult` whose ``recovery`` field tells the caller
    which strategy to apply next.

    Dispatch order (plan §5 Phase 2 is stated in two layers):

      **Primary (isinstance + status_code)**: auth → billing → rate_limit →
      context_overflow → overloaded → server_error → timeout → format_error.

      **Message-pattern fallback**: interleaved with the primary — checked
      after the corresponding type/status check in the same priority rank —
      *except for auth-by-message*, which runs AFTER all other patterns so
      a message like ``"invalid api key: payment required"`` classifies as
      ``billing`` (the more actionable reason) rather than ``auth``. That
      intentional deviation is pinned by
      ``test_auth_message_defers_to_billing_match``.

      Finally ``upstream_unavailable`` → ``unknown``.

    Raises:
        TypeError: if ``exc`` is not a :class:`BaseException`. Surfaces
            call-site bugs early instead of silently classifying as unknown.
    """
    if not isinstance(exc, BaseException):
        raise TypeError(
            f"classify_error expected BaseException, got {type(exc).__name__}"
        )
    status_code = _status_code(exc)
    message = str(exc).lower()

    # 1. auth — litellm AuthenticationError / PermissionDeniedError, 401/403,
    #    or message patterns.
    if isinstance(exc, _lexc.AuthenticationError) or isinstance(
        exc, _lexc.PermissionDeniedError
    ):
        return _build(FailoverReason.auth, status_code, str(exc))
    if status_code in (401, 403):
        return _build(FailoverReason.auth, status_code, str(exc))

    # 2. billing — BudgetExceededError or 402 or explicit billing patterns.
    #    Checked before auth-by-message so "exceeded quota" is not misread
    #    as an auth issue.
    if isinstance(exc, _lexc.BudgetExceededError):
        return _build(FailoverReason.billing, status_code, str(exc))
    if status_code == 402:
        return _build(FailoverReason.billing, status_code, str(exc))
    if _any(message, _BILLING_PATTERNS):
        return _build(FailoverReason.billing, status_code, str(exc))

    # 3. rate_limit — RateLimitError / 429 / message.
    if isinstance(exc, _lexc.RateLimitError):
        return _build(FailoverReason.rate_limit, status_code, str(exc))
    if status_code == 429:
        return _build(FailoverReason.rate_limit, status_code, str(exc))
    if _any(message, _RATE_LIMIT_PATTERNS):
        return _build(FailoverReason.rate_limit, status_code, str(exc))

    # 4. context_overflow — MUST come before format_error since
    #    ContextWindowExceededError inherits from BadRequestError (400).
    if isinstance(exc, _lexc.ContextWindowExceededError):
        return _build(FailoverReason.context_overflow, status_code, str(exc))
    if _any(message, _CONTEXT_OVERFLOW_PATTERNS):
        return _build(FailoverReason.context_overflow, status_code, str(exc))

    # 5. overloaded — 503/529 / ServiceUnavailableError / message.
    if isinstance(exc, _lexc.ServiceUnavailableError):
        return _build(FailoverReason.overloaded, status_code, str(exc))
    if status_code in (503, 529):
        return _build(FailoverReason.overloaded, status_code, str(exc))
    if _any(message, _OVERLOADED_PATTERNS):
        return _build(FailoverReason.overloaded, status_code, str(exc))

    # 6. server_error — 500/502 / InternalServerError / BadGatewayError / message.
    if isinstance(exc, (_lexc.InternalServerError, _lexc.BadGatewayError)):
        return _build(FailoverReason.server_error, status_code, str(exc))
    if status_code in (500, 502):
        return _build(FailoverReason.server_error, status_code, str(exc))
    if _any(message, _SERVER_ERROR_PATTERNS):
        return _build(FailoverReason.server_error, status_code, str(exc))

    # 7. timeout — litellm Timeout / stdlib TimeoutError / pattern.
    if isinstance(exc, _lexc.Timeout):
        return _build(FailoverReason.timeout, status_code, str(exc))
    if isinstance(exc, TimeoutError):
        return _build(FailoverReason.timeout, status_code, str(exc))
    if _any(message, _TIMEOUT_PATTERNS):
        return _build(FailoverReason.timeout, status_code, str(exc))

    # 8. format_error — generic 400 / BadRequestError / pattern.
    #    ContextWindowExceededError has already returned above, so this
    #    branch only catches 'true' BadRequest shapes.
    if isinstance(exc, _lexc.BadRequestError):
        return _build(FailoverReason.format_error, status_code, str(exc))
    if status_code == 400:
        return _build(FailoverReason.format_error, status_code, str(exc))
    if _any(message, _FORMAT_ERROR_PATTERNS):
        return _build(FailoverReason.format_error, status_code, str(exc))

    # 8b. auth — message-only check runs *after* the priority block so it
    #     does not mask more specific billing/rate_limit messages.
    if _any(message, _AUTH_PATTERNS):
        return _build(FailoverReason.auth, status_code, str(exc))

    # 9. upstream_unavailable — matrix-specific marker (plan §3/§5). Probed
    #    late so specific reasons win when the message contains both.
    if _any(message, _UPSTREAM_UNAVAILABLE_PATTERNS):
        return _build(FailoverReason.upstream_unavailable, status_code, str(exc))

    # 10. unknown — safe retryable fallback.
    return _build(FailoverReason.unknown, status_code, str(exc))


def _status_code(exc: BaseException) -> Optional[int]:
    """Walk the exception + cause chain for an HTTP status code.

    Accepts both ``int`` and numeric-string codes — some providers set
    ``status_code = "429"`` from JSON bodies.
    """
    current: Optional[BaseException] = exc
    for _ in range(5):
        if current is None:
            break
        for attr in ("status_code", "status"):
            code = getattr(current, attr, None)
            if isinstance(code, int):
                if attr == "status" and not (100 <= code < 600):
                    continue
                return code
            if isinstance(code, str) and code.strip().isdigit():
                parsed = int(code.strip())
                if 100 <= parsed < 600:
                    return parsed
        next_ = getattr(current, "__cause__", None) or getattr(
            current, "__context__", None
        )
        if next_ is None or next_ is current:
            break
        current = next_
    return None


def _build(
    reason: FailoverReason, status_code: Optional[int], message: str
) -> ClassificationResult:
    return ClassificationResult(
        reason=reason,
        recovery=_RECOVERY[reason],
        status_code=status_code,
        message=message,
        retryable=reason not in _NON_RETRYABLE,
    )
