# Rate Limiter — exec-12 Phase 2.3
# Per-tool call counter + per-session token budget + grace termination.
# Scoped by thread_id. Integrates with consent system via check_consent().

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from agent.consent.config import get_consent_config

logger = logging.getLogger(__name__)


@dataclass
class SessionUsage:
    """Tracks usage counters for a single session/thread."""
    tool_calls_total: int = 0
    tool_calls_per_tool: dict[str, int] = field(default_factory=dict)
    tokens_used: int = 0
    iterations: int = 0
    created_at: float = field(default_factory=time.monotonic)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    reason: str = ""
    is_grace_warning: bool = False


class SessionRateLimiter:
    """Per-session rate limiter with per-tool counters and token budget."""

    def __init__(self) -> None:
        # {thread_id: SessionUsage}
        self._sessions: dict[str, SessionUsage] = {}

    def _get_session(self, thread_id: str) -> SessionUsage:
        if thread_id not in self._sessions:
            self._sessions[thread_id] = SessionUsage()
        return self._sessions[thread_id]

    def check(self, thread_id: str, tool_name: str) -> RateLimitResult:
        """Check if a tool call is allowed under rate limits."""
        config = get_consent_config().rate_limits
        session = self._get_session(thread_id)

        # 1. Per-session total tool calls
        if config.max_tool_calls_total > 0 and session.tool_calls_total >= config.max_tool_calls_total:
            return RateLimitResult(
                allowed=False,
                reason=f"Session tool call limit reached ({config.max_tool_calls_total})",
            )

        # 2. Per-tool call limit
        tool_limit_cfg = config.per_tool.get(tool_name)
        if tool_limit_cfg and tool_limit_cfg.max_calls > 0:
            current = session.tool_calls_per_tool.get(tool_name, 0)
            if current >= tool_limit_cfg.max_calls:
                return RateLimitResult(
                    allowed=False,
                    reason=f"Tool '{tool_name}' call limit reached ({tool_limit_cfg.max_calls})",
                )

        # 3. Token budget
        if config.max_tokens_per_session > 0 and session.tokens_used >= config.max_tokens_per_session:
            return RateLimitResult(
                allowed=False,
                reason=f"Session token budget exhausted ({config.max_tokens_per_session})",
            )

        # 4. Grace termination warning
        max_iter = config.get_max_iterations()
        if config.grace_iterations > 0 and max_iter > 0:
            remaining = max_iter - session.iterations
            if 0 < remaining <= config.grace_iterations:
                return RateLimitResult(
                    allowed=True,
                    reason=f"Warning: {remaining} iteration(s) remaining before hard stop",
                    is_grace_warning=True,
                )

        return RateLimitResult(allowed=True)

    def record_tool_call(self, thread_id: str, tool_name: str) -> None:
        """Record a tool call after execution."""
        session = self._get_session(thread_id)
        session.tool_calls_total += 1
        session.tool_calls_per_tool[tool_name] = session.tool_calls_per_tool.get(tool_name, 0) + 1

    def record_tokens(self, thread_id: str, tokens: int) -> None:
        """Record token usage (input + output)."""
        session = self._get_session(thread_id)
        session.tokens_used += tokens

    def record_iteration(self, thread_id: str) -> None:
        """Record a graph iteration."""
        session = self._get_session(thread_id)
        session.iterations += 1

    def get_usage(self, thread_id: str) -> SessionUsage:
        """Get current usage for a session."""
        return self._get_session(thread_id)

    def clear(self, thread_id: str) -> None:
        """Clear usage for a session."""
        self._sessions.pop(thread_id, None)


# ── Singleton ──────────────────────────────────────────────────────────────

_limiter: SessionRateLimiter | None = None


def get_rate_limiter() -> SessionRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = SessionRateLimiter()
    return _limiter
