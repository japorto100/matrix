"""A2A Delegation Node — delegiert Tasks an Remote-Agents (exec-10 Phase 4.3).

Wenn ein Agent lokal nicht verfuegbar ist oder explizit remote sein soll,
wird die Anfrage via A2A Protocol an einen externen Agent geschickt.

Lokal: Sub-Graph (schnell, kein Netzwerk)
Remote: A2A Client → HTTP → Remote Agent → Response
"""

from __future__ import annotations

import logging
import os
from typing import Any

from agent.a2a.client import A2AClient
from agent.graph.state import AgentGraphState

logger = logging.getLogger(__name__)

# Remote Agent URLs (konfigurierbar via ENV)
REMOTE_AGENTS: dict[str, str] = {}


def _load_remote_agents() -> dict[str, str]:
    """Laedt Remote-Agent URLs aus Environment."""
    global REMOTE_AGENTS
    if REMOTE_AGENTS:
        return REMOTE_AGENTS

    # Format: AGENT_REMOTE_{ROLE}=http://host:port
    for key, value in os.environ.items():
        if key.startswith("AGENT_REMOTE_"):
            role = key.removeprefix("AGENT_REMOTE_").lower()
            REMOTE_AGENTS[role] = value.strip()

    return REMOTE_AGENTS


async def a2a_delegate_node(state: AgentGraphState) -> dict[str, Any]:
    """Delegiert die aktuelle Anfrage an einen Remote-Agent via A2A.

    Wird nur aufgerufen wenn der Orchestrator einen Remote-Agent fuer
    die aktuelle Rolle konfiguriert hat.
    """
    role = state.get("current_role", "")
    remote_agents = _load_remote_agents()

    if role not in remote_agents:
        logger.debug("No remote agent for role '%s', skipping A2A delegation", role)
        return {}

    agent_url = remote_agents[role]
    messages = state.get("messages", [])

    # Letzte User-Message als Anfrage
    user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            user_msg = msg["content"]
            break

    if not user_msg:
        return {}

    logger.info("A2A delegation: role=%s → %s", role, agent_url)

    client = A2AClient()
    try:
        task = await client.send_message(
            agent_url=agent_url,
            message=user_msg,
            context=f"Delegated from orchestrator, role: {role}",
        )

        if task.state == "completed" and task.result:
            return {
                "messages": [{"role": "assistant", "content": f"[{role} via A2A]: {task.result}"}],
                "final_response": task.result,
                "done": True,
            }
        else:
            error = task.error or "Unknown A2A error"
            logger.warning("A2A delegation failed: %s", error)
            return {
                "messages": [{"role": "assistant", "content": f"[{role} A2A error]: {error}"}],
            }
    finally:
        await client.close()
