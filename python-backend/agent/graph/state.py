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
