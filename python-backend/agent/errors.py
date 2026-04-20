# Agent error hierarchy — Phase 22g / ABP.1
# Pattern: AgentZero RepairableException vs. CriticalError distinction
# RepairableError → loop can retry / ask for clarification
# CriticalError   → loop must abort immediately

from __future__ import annotations


class RepairableError(Exception):
    """Recoverable error — agent loop may retry or degrade gracefully."""


class CriticalError(Exception):
    """Unrecoverable error — loop must abort; no further iterations."""


class ToolValidationError(RepairableError):
    """Tool input failed policy/schema validation — safe to surface to LLM as error result."""

    def __init__(self, tool_name: str, reason: str) -> None:
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Tool '{tool_name}' validation failed: {reason}")


class CapabilityViolationError(CriticalError):
    """Tool is outside the agent's capability envelope — abort immediately."""

    def __init__(self, tool_name: str, envelope_class: str) -> None:
        self.tool_name = tool_name
        super().__init__(
            f"Tool '{tool_name}' not allowed for agent class '{envelope_class}'"
        )


class RetrievalAccessDeniedError(CriticalError):
    """ACL or sensitivity check blocked a retrieval query."""

    def __init__(self, scope: str, reason: str) -> None:
        super().__init__(f"Retrieval denied for scope '{scope}': {reason}")


class MaxIterationsExceededError(CriticalError):
    """Agent loop hit MAX_ITERATIONS without end_turn."""

    def __init__(self, max_iter: int) -> None:
        super().__init__(f"Agent loop exceeded maximum iterations ({max_iter})")


class CredentialExhaustedError(RepairableError):
    """exec-hermes Phase-B P1: :class:`CredentialPool.acquire` returned
    ``None`` — no usable API key for the requested ``(user, provider)``.

    Possible causes:
    * The only key was rate-limited and its cooldown TTL hasn't expired
    * The only key was auth-rejected (user needs to replace it)
    * No key configured for this provider (``agent.user_credentials`` empty)

    The runner translates this into a user-facing ``ErrorPacket`` with
    ``failover_reason=billing`` or similar so the UI can prompt the user.
    """

    def __init__(self, user_id: str, provider: str, reason: str = "no usable credential") -> None:
        self.user_id = user_id
        self.provider = provider
        super().__init__(
            f"CredentialPool exhausted for user={user_id!r} provider={provider!r}: {reason}"
        )
