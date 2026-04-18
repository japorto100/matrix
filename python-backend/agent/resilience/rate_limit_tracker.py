"""Rate-limit tracking for LiteLLM gateway responses.

Enterprise port of ``_ref/hermes-agent/agent/rate_limit_tracker.py``:

- :func:`RateLimitRegistry.capture_from_response` takes ``user_id`` and
  ``provider_key_id`` so each caller's quota is tracked independently.
- :class:`RateLimitRegistry` is an in-memory store keyed on
  ``(user_id, provider_key_id, window)``. Persistence (Prometheus scrape,
  OpenObserve) lives outside this module per exec-17.
- :meth:`RateLimitBucket.to_prometheus_dict` emits a label+metric pair
  suitable for scrape-style monitoring.
- LiteLLM hides rate-limit headers under
  ``response._hidden_params["additional_headers"]``. The extractor walks
  that path first and falls back to ``response.headers`` or a dict-shaped
  response so this module works with raw httpx responses too.

Header schema (12 headers; four windows):

    x-ratelimit-limit-requests        x-ratelimit-limit-requests-1h
    x-ratelimit-remaining-requests    x-ratelimit-remaining-requests-1h
    x-ratelimit-reset-requests        x-ratelimit-reset-requests-1h
    x-ratelimit-limit-tokens          x-ratelimit-limit-tokens-1h
    x-ratelimit-remaining-tokens      x-ratelimit-remaining-tokens-1h
    x-ratelimit-reset-tokens          x-ratelimit-reset-tokens-1h
"""
from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "RateLimitBucket",
    "RateLimitRegistry",
    "WINDOWS",
]


#: Window identifiers — mirror the x-ratelimit-* header suffix.
WINDOWS: tuple[str, ...] = ("requests", "requests-1h", "tokens", "tokens-1h")


@dataclass
class RateLimitBucket:
    """One rate-limit window for a specific (user, provider-key) pair."""

    limit: int = 0
    remaining: int = 0
    reset_seconds: float = 0.0
    captured_at: float = 0.0

    # Identity — set by the registry when a bucket is captured.
    window: str = ""
    user_id: str = ""
    provider: str = ""
    provider_key_id: str = ""

    @property
    def used(self) -> int:
        return max(0, self.limit - self.remaining)

    @property
    def usage_pct(self) -> float:
        if self.limit <= 0:
            return 0.0
        return (self.used / self.limit) * 100.0

    @property
    def remaining_seconds_now(self) -> float:
        """Estimated seconds until reset, compensated for age of capture."""
        if self.captured_at <= 0:
            return self.reset_seconds
        elapsed = time.time() - self.captured_at
        return max(0.0, self.reset_seconds - elapsed)

    def to_prometheus_dict(self) -> dict:
        """Label+metric dict suitable for OpenObserve / Prometheus scrape."""
        return {
            "labels": {
                "user_id": self.user_id,
                "provider": self.provider,
                "provider_key_id": self.provider_key_id,
                "window": self.window,
            },
            "metrics": {
                "limit": self.limit,
                "remaining": self.remaining,
                "used": self.used,
                "usage_pct": self.usage_pct,
                "reset_seconds": self.reset_seconds,
                "captured_at": self.captured_at,
            },
        }


# ---------------------------------------------------------------------------
# Header extraction
# ---------------------------------------------------------------------------

def _extract_headers(response: Any) -> Mapping[str, str]:
    """Extract rate-limit headers from a LiteLLM response (or raw shape).

    LiteLLM canonically exposes provider headers under
    ``response._hidden_params["additional_headers"]``. For robustness
    against raw httpx responses and dict shapes, the extractor falls back
    to ``response.headers`` or ``response["headers"]``.
    """
    if response is None:
        return {}

    hidden = getattr(response, "_hidden_params", None)
    if isinstance(hidden, Mapping):
        additional = hidden.get("additional_headers")
        if isinstance(additional, Mapping):
            return additional

    raw_headers = getattr(response, "headers", None)
    if isinstance(raw_headers, Mapping):
        return raw_headers

    if isinstance(response, Mapping):
        nested = response.get("headers")
        if isinstance(nested, Mapping):
            return nested

    return {}


def _safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_window(
    headers_lower: Mapping[str, str],
    window: str,
    *,
    user_id: str,
    provider_key_id: str,
    provider: str,
    now: float,
) -> RateLimitBucket:
    limit = _safe_int(headers_lower.get(f"x-ratelimit-limit-{window}"))
    remaining = _safe_int(headers_lower.get(f"x-ratelimit-remaining-{window}"))
    reset = _safe_float(headers_lower.get(f"x-ratelimit-reset-{window}"))
    return RateLimitBucket(
        limit=limit,
        remaining=remaining,
        reset_seconds=reset,
        captured_at=now if limit or remaining or reset else 0.0,
        window=window,
        user_id=user_id,
        provider=provider,
        provider_key_id=provider_key_id,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass
class RateLimitRegistry:
    """In-memory per-(user, provider-key) rate-limit bucket store.

    **Not thread-safe.** The registry uses a plain dict with no lock. Safe
    under single-threaded async: one asyncio task per loop modifies the
    registry, and capture calls are short non-blocking dict writes so the
    event loop never yields inside one. If the matrix harness ever calls
    ``capture_from_response`` from multiple OS threads or across event
    loops, wrap the instance with ``threading.Lock`` / ``asyncio.Lock``
    at the call site.
    """

    _buckets: dict[tuple[str, str, str], RateLimitBucket] = field(default_factory=dict)

    def capture_from_response(
        self,
        response: Any,
        *,
        user_id: str,
        provider_key_id: str,
        provider: str = "",
    ) -> list[RateLimitBucket]:
        """Parse rate-limit headers from ``response`` and store per-window buckets.

        Returns the list of buckets captured (always one per window — missing
        headers produce zero-valued buckets, per plan §5 Phase 3).
        """
        raw = _extract_headers(response)
        lowered = {str(k).lower(): v for k, v in raw.items()}
        now = time.time()

        captured: list[RateLimitBucket] = []
        for window in WINDOWS:
            bucket = _parse_window(
                lowered,
                window,
                user_id=user_id,
                provider_key_id=provider_key_id,
                provider=provider,
                now=now,
            )
            self._buckets[(user_id, provider_key_id, window)] = bucket
            captured.append(bucket)
        return captured

    def get(
        self, user_id: str, provider_key_id: str, window: str
    ) -> RateLimitBucket | None:
        return self._buckets.get((user_id, provider_key_id, window))

    def all(self) -> list[RateLimitBucket]:
        return list(self._buckets.values())

    def clear(self) -> None:
        self._buckets.clear()

    def __len__(self) -> int:
        return len(self._buckets)
