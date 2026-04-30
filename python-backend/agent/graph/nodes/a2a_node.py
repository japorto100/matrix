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


def _max_spawn_depth() -> int:
    raw = os.environ.get("AGENT_A2A_MAX_SPAWN_DEPTH", "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _spawn_depth(state: AgentGraphState) -> int:
    try:
        return max(0, int(state.get("spawn_depth", 0)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _delegation_context(*, role: str, state: AgentGraphState, next_depth: int, max_depth: int) -> str:
    thread_id = str(state.get("thread_id", "") or "")
    return (
        "Delegated from Matrix orchestrator; "
        f"role:{role}; parent_thread_id:{thread_id}; "
        f"spawn_depth:{next_depth}; max_spawn_depth:{max_depth}; "
        "memory_scope:explicit_context_only"
    )


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

    current_depth = _spawn_depth(state)
    max_depth = _max_spawn_depth()
    if current_depth >= max_depth:
        logger.info(
            "A2A delegation disabled by spawn depth: role=%s current=%d max=%d",
            role,
            current_depth,
            max_depth,
        )
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
        next_depth = current_depth + 1
        task = await client.send_message(
            agent_url=agent_url,
            message=user_msg,
            context=_delegation_context(
                role=role,
                state=state,
                next_depth=next_depth,
                max_depth=max_depth,
            ),
        )

        if task.state == "completed" and task.result:
            return {
                "messages": [
                    {"role": "assistant", "content": f"[{role} via A2A]: {task.result}"}
                ],
                "final_response": task.result,
                "done": True,
            }
        else:
            error = task.error or "Unknown A2A error"
            logger.warning("A2A delegation failed: %s", error)
            return {
                "messages": [
                    {"role": "assistant", "content": f"[{role} A2A error]: {error}"}
                ],
            }
    finally:
        await client.close()
