"""AgentGraphState — shared state fuer den LangGraph Agent.

Alle Nodes lesen und schreiben auf diesen State.
Reducer-Annotationen steuern wie Updates aggregiert werden.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any

from typing_extensions import TypedDict


class ToolCall(TypedDict):
    """Pending tool call from LLM."""

    tool_call_id: str
    tool_name: str
    tool_input: dict[str, Any]


class ToolResult(TypedDict):
    """Result of a tool execution."""

    tool_call_id: str
    tool_name: str
    result: dict[str, Any] | str
    error: str | None


class AgentGraphState(TypedDict):
    """Shared state for the LangGraph agent graph.

    Reducer annotations:
    - messages: append (conversation history grows)
    - tool_results: append (results accumulate per iteration)
    - iteration: overwrite (counter)
    """

    # Conversation messages (user + assistant + tool results)
    messages: Annotated[list[dict[str, Any]], operator.add]

    # Current pending tool calls from LLM
    tool_calls: list[ToolCall]

    # Tool definitions allowed for this turn. ``None``/missing means legacy
    # registry fallback; an empty list means tools are explicitly disabled.
    tool_definitions: list[dict[str, Any]] | None

    # Accumulated tool results
    tool_results: Annotated[list[ToolResult], operator.add]

    # Current iteration counter
    iteration: int

    # Max iterations before forced stop
    max_iterations: int

    # Current agent role (for sub-graph routing)
    current_role: str

    # System prompt (can change per role)
    system_prompt: str

    # Model to use
    model: str

    # exec-16: Per-user API key (aus DB, via extra_body an LiteLLM durchgereicht)
    api_key: str | None

    # Reasoning effort (low/medium/high)
    reasoning_effort: str | None

    # Aggregated usage across all LLM calls in the run
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    cached_tokens: int
    token_usage: int

    # Provider/model metadata for the latest run
    llm_provider: str
    llm_model: str

    # Runtime context diagnostics surfaced to frontend/control
    source_layer_counts: dict[str, int]
    context_blocks: list[dict[str, Any]]
    degradation_flags: list[str]

    # Final response text (set by synthesize node)
    final_response: str

    # Whether the agent is done
    done: bool

    # Thread ID for checkpointing
    thread_id: str

    # User ID
    user_id: str

    # Agent class (advisory/executor) — used by consent system
    agent_class: str

    # User role from Go Gateway (viewer/analyst/trader/admin)
    user_role: str

    # Whether approval_node may use resumable LangGraph interrupts.
    approval_interrupts: bool

    # ADR-001 G4: A/B experiment row id (UUID) when this turn runs under
    # an active dispatcher experiment. Used by the router_node smart-
    # routing decision to mark the routing dimension on the same
    # ab_experiments row via fire-and-forget UPDATE. Empty string when
    # not under an experiment.
    ab_row_id: str

    # ADR-001 P1: smart-routing decision output produced by router_node
    # (runs START → memory_recall → router → llm_call). Consumed by
    # llm_node for span-attributes + final model selection. Default
    # values mean "router did not run" — safe for ad-hoc graph calls
    # that skip the dispatcher entry point.
    routing_reason: str
    routing_used: bool
    routing_picked_model: str

    # Observability label for Meta-Harness route-decision traces.
    runner_variant: str
