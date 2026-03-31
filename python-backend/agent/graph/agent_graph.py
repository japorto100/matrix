"""Agent Graph — LangGraph StateGraph fuer den Trading Agent.

Nodes: llm_call → approval_gate → tool_execute → (loop back to llm_call)
                                                 → synthesize (wenn keine tool_calls)

Ersetzt den manuellen while-Loop aus agent/loop.py.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.graph.nodes.approval_node import approval_node
from agent.graph.nodes.llm_node import llm_node
from agent.graph.nodes.tool_node import tool_node
from agent.graph.state import AgentGraphState

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


def _route_after_llm(state: AgentGraphState) -> str:
    """Routing nach LLM Call: tool_calls vorhanden → approval, sonst → Ende."""
    if state.get("done"):
        return "end"
    if state.get("tool_calls"):
        return "approval"
    return "end"


def _route_after_tools(state: AgentGraphState) -> str:
    """Routing nach Tool Execution: max iterations erreicht → Ende, sonst → LLM."""
    iteration = state.get("iteration", 0) + 1
    max_iter = state.get("max_iterations", MAX_ITERATIONS)
    if iteration >= max_iter:
        return "end"
    return "llm"


async def _increment_iteration(state: AgentGraphState) -> dict[str, Any]:
    """Zaehlt die Iteration hoch."""
    return {"iteration": state.get("iteration", 0) + 1}


def create_agent_graph(checkpointer: Any | None = None) -> Any:
    """Erstellt und kompiliert den Agent StateGraph.

    Returns:
        Compiled LangGraph graph ready for invoke/stream.
    """
    graph = StateGraph(AgentGraphState)

    # Nodes registrieren
    graph.add_node("llm_call", llm_node)
    graph.add_node("approval_gate", approval_node)
    graph.add_node("tool_execute", tool_node)
    graph.add_node("increment", _increment_iteration)

    # Edges
    graph.add_edge(START, "llm_call")

    # Nach LLM: tool_calls → approval, sonst → Ende
    graph.add_conditional_edges(
        "llm_call",
        _route_after_llm,
        {"approval": "approval_gate", "end": END},
    )

    # Nach Approval → Tool Execution
    graph.add_edge("approval_gate", "tool_execute")

    # Nach Tools → Increment → Routing (zurueck zu LLM oder Ende)
    graph.add_edge("tool_execute", "increment")
    graph.add_conditional_edges(
        "increment",
        _route_after_tools,
        {"llm": "llm_call", "end": END},
    )

    # Kompilieren
    if checkpointer is None:
        checkpointer = MemorySaver()

    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval_gate"],  # Human-in-the-loop
    )

    logger.info("Agent graph compiled (nodes: llm_call, approval_gate, tool_execute, increment)")
    return compiled
