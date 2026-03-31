"""Multi-Agent Orchestrator — koordiniert Trading-Rollen via LangGraph (exec-10 Phase 2).

Task Decomposition: User-Anfrage → relevante Rollen aktivieren
Parallel: Fundamentals + Sentiment + Technical (unabhaengig)
Sequential: Researcher → Trader → RiskManager (abhaengig)

Inspiriert von TauricResearch/TradingAgents Graph-Architektur.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.graph.nodes.llm_node import llm_node
from agent.graph.nodes.tool_node import tool_node
from agent.graph.state import AgentGraphState
from agent.roles import TRADING_ROLE_PROMPTS, TRADING_ROLE_TOOLS, TradingRole

logger = logging.getLogger(__name__)


def _create_role_node(role: TradingRole):
    """Factory: erstellt einen LLM Node mit rollen-spezifischem Prompt + Tools."""

    async def role_node(state: AgentGraphState) -> dict[str, Any]:
        # Rollen-spezifischen System-Prompt setzen
        role_prompt = TRADING_ROLE_PROMPTS[role]
        base_prompt = state.get("system_prompt", "")
        combined = f"{base_prompt}\n\n## Current Role: {role.value}\n{role_prompt}"

        # State mit Rollen-Prompt updaten und LLM aufrufen
        role_state = {**state, "system_prompt": combined, "current_role": role.value}
        result = await llm_node(role_state)
        return result

    role_node.__name__ = f"role_{role.value}"
    return role_node


async def _aggregate_analyses(state: AgentGraphState) -> dict[str, Any]:
    """Sammelt Ergebnisse der Analyse-Rollen und bereitet sie fuer den Researcher auf."""
    messages = state.get("messages", [])
    # Die letzten Assistant-Messages sind die Rollen-Outputs
    analysis_summary = "\n\n".join(
        f"[{msg.get('role', 'unknown')}]: {msg.get('content', '')}"
        for msg in messages[-6:]  # Letzte 6 Messages (3 Rollen × 2)
        if isinstance(msg.get("content"), str) and msg.get("role") == "assistant"
    )

    return {
        "messages": [{
            "role": "user",
            "content": (
                "Based on the analyses above, provide a balanced research summary "
                "with bull and bear arguments, key risks, and a confidence level.\n\n"
                f"Analyses:\n{analysis_summary}"
            ),
        }],
    }


def create_orchestrator_graph(checkpointer: Any | None = None) -> Any:
    """Erstellt den Multi-Agent Orchestrator Graph.

    Flow:
    START → [Fundamentals, Sentiment, Technical] (parallel)
          → Aggregate → Researcher → Trader → RiskManager → END
    """
    graph = StateGraph(AgentGraphState)

    # Analyse-Rollen Nodes
    graph.add_node("fundamentals", _create_role_node(TradingRole.FUNDAMENTALS))
    graph.add_node("sentiment", _create_role_node(TradingRole.SENTIMENT))
    graph.add_node("technical", _create_role_node(TradingRole.TECHNICAL))

    # Aggregation
    graph.add_node("aggregate", _aggregate_analyses)

    # Sequential Rollen
    graph.add_node("researcher", _create_role_node(TradingRole.RESEARCHER))
    graph.add_node("trader", _create_role_node(TradingRole.TRADER))
    graph.add_node("risk_manager", _create_role_node(TradingRole.RISK_MANAGER))

    # Tool execution (shared)
    graph.add_node("tools", tool_node)

    # Edges: Parallel Analyse
    graph.add_edge(START, "fundamentals")
    graph.add_edge(START, "sentiment")
    graph.add_edge(START, "technical")

    # Alle Analysen → Aggregate
    graph.add_edge("fundamentals", "aggregate")
    graph.add_edge("sentiment", "aggregate")
    graph.add_edge("technical", "aggregate")

    # Sequential: Researcher → Trader → RiskManager
    graph.add_edge("aggregate", "researcher")
    graph.add_edge("researcher", "trader")
    graph.add_edge("trader", "risk_manager")
    graph.add_edge("risk_manager", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("Orchestrator graph compiled (6 roles + aggregate)")
    return compiled
