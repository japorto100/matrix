# Trading policy validators — Phase 22g / ABP.2
# Validates tool calls against trading policy before execution.
# These are domain-level constraints that no generic framework expresses.

from __future__ import annotations

from typing import TYPE_CHECKING

from agent.errors import ToolValidationError

if TYPE_CHECKING:
    from agent.context import AgentExecutionContext


# Tools that can trigger order placement or position mutation
_ORDER_TOOLS = frozenset({"place_order", "cancel_order", "modify_position"})
# Tools that require human approval in advisory mode
_APPROVAL_REQUIRED_ADVISORY = frozenset({"set_chart_state"})


def validate_tool_call(tool_name: str, tool_input: dict, ctx: "AgentExecutionContext") -> None:
    """
    Run domain-level validation on a tool call before execution.
    Called by run_agent_loop before each tool.execute().
    Raises ToolValidationError for policy violations — result is returned to LLM.
    Raises CapabilityViolation for capability envelope violations — loop aborts.
    """
    # Hard block: advisory agents cannot place orders
    if ctx.agent_class == "advisory" and tool_name in _ORDER_TOOLS:
        raise ToolValidationError(
            tool_name,
            "Advisory agent is not allowed to place or modify orders. "
            "This action requires explicit user permission.",
        )

    # Validate capability envelope
    from agent.context import ENVELOPES
    envelope = ENVELOPES.get(ctx.agent_class)
    if envelope:
        envelope.check(tool_name)


def needs_approval(tool_name: str, ctx: "AgentExecutionContext") -> bool:
    """
    ABP.3: Return True if this tool call requires human approval before execution.
    Advisory agents need approval for any mutation tool.
    """
    if ctx.agent_class == "advisory" and tool_name in _APPROVAL_REQUIRED_ADVISORY:
        return True
    return False
