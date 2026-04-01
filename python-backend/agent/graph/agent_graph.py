"""Agent Graph — LangGraph StateGraph fuer den Trading Agent.

Flow: START → memory_recall → llm_call → [approval → tools → increment →]* → memory_retain → END

exec-11: memory_recall (VOR LLM) + memory_retain (NACH LLM) Nodes hinzugefuegt.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.graph.nodes.approval_node import approval_node
from agent.graph.nodes.llm_node import llm_node
from agent.graph.nodes.memory_node import memory_recall_node, memory_retain_node
from agent.graph.nodes.tool_node import tool_node
from agent.graph.state import AgentGraphState

logger = logging.getLogger(__name__)

def _get_max_iterations() -> int:
    try:
        from agent.consent.config import get_consent_config
        return get_consent_config().rate_limits.get_max_iterations()
    except Exception:
        return int(os.environ.get("AGENT_MAX_ITERATIONS", "10"))

MAX_ITERATIONS = _get_max_iterations()


def _route_after_llm(state: AgentGraphState) -> str:
    """Routing nach LLM Call: tool_calls → approval, sonst → retain."""
    if state.get("done"):
        return "retain"
    if state.get("tool_calls"):
        return "approval"
    return "retain"


def _route_after_tools(state: AgentGraphState) -> str:
    """Routing nach Tool Execution: max iterations → retain, sonst → LLM."""
    iteration = state.get("iteration", 0) + 1
    max_iter = state.get("max_iterations", MAX_ITERATIONS)
    if iteration >= max_iter:
        return "retain"
    return "llm"


async def _increment_iteration(state: AgentGraphState) -> dict[str, Any]:
    """Zaehlt die Iteration hoch und meldet sie an den Rate Limiter."""
    thread_id = state.get("thread_id", "")
    if thread_id:
        from agent.consent.rate_limiter import get_rate_limiter
        get_rate_limiter().record_iteration(thread_id)
    return {"iteration": state.get("iteration", 0) + 1}


def create_agent_graph(checkpointer: Any | None = None) -> Any:
    """Erstellt und kompiliert den Agent StateGraph.

    Flow: START → memory_recall → llm_call → [approval → tools → increment →]* → memory_retain → END
    """
    graph = StateGraph(AgentGraphState)

    # Nodes registrieren
    graph.add_node("memory_recall", memory_recall_node)
    graph.add_node("llm_call", llm_node)
    graph.add_node("approval_gate", approval_node)
    graph.add_node("tool_execute", tool_node)
    graph.add_node("increment", _increment_iteration)
    graph.add_node("memory_retain", memory_retain_node)

    # START → Memory Recall → LLM
    graph.add_edge(START, "memory_recall")
    graph.add_edge("memory_recall", "llm_call")

    # Nach LLM: tool_calls → approval, sonst → retain
    graph.add_conditional_edges(
        "llm_call",
        _route_after_llm,
        {"approval": "approval_gate", "retain": "memory_retain"},
    )

    # Nach Approval → Tool Execution
    graph.add_edge("approval_gate", "tool_execute")

    # Nach Tools → Increment → Routing (zurueck zu LLM oder retain)
    graph.add_edge("tool_execute", "increment")
    graph.add_conditional_edges(
        "increment",
        _route_after_tools,
        {"llm": "llm_call", "retain": "memory_retain"},
    )

    # Memory Retain → END
    graph.add_edge("memory_retain", END)

    # Kompilieren — #13 fix: PostgreSQL checkpointer wenn DB verfuegbar
    if checkpointer is None:
        db_url = os.environ.get("HINDSIGHT_DB_URL")
        if db_url:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
                logger.info("LangGraph checkpointer: PostgreSQL (persistent)")
            except Exception:
                checkpointer = MemorySaver()
                logger.info("LangGraph checkpointer: MemorySaver (in-memory fallback)")
        else:
            checkpointer = MemorySaver()

    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval_gate"],
    )

    logger.info("Agent graph compiled (nodes: memory_recall, llm_call, approval_gate, tool_execute, increment, memory_retain)")
    return compiled
