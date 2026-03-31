"""Approval Gate Node — Human-in-the-Loop via LangGraph interrupt.

Prueft ob pending tool_calls eine Approval brauchen.
Wenn ja: interrupt() → wartet auf User-Entscheidung → resume.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.types import interrupt

from agent.graph.state import AgentGraphState
from agent.validators.trading import needs_approval

logger = logging.getLogger(__name__)


async def approval_node(state: AgentGraphState) -> dict[str, Any]:
    """Prueft tool_calls auf Approval-Bedarf und interrupted wenn noetig."""
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        return {}

    approved_calls = []
    for tc in tool_calls:
        if needs_approval(tc["tool_name"]):
            # Human-in-the-loop: interrupt und warte auf Approval
            decision = interrupt({
                "type": "approval_request",
                "tool_call_id": tc["tool_call_id"],
                "tool_name": tc["tool_name"],
                "tool_input": tc["tool_input"],
            })

            if decision == "approve":
                approved_calls.append(tc)
                logger.info("Tool approved: %s", tc["tool_name"])
            else:
                logger.info("Tool denied: %s", tc["tool_name"])
        else:
            # Kein Approval noetig → direkt durchlassen
            approved_calls.append(tc)

    return {"tool_calls": approved_calls}
