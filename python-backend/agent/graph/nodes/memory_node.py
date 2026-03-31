"""Memory Nodes — Recall + Retain als LangGraph Nodes (exec-11).

memory_recall_node: VOR LLM-Call — holt relevante Memories, injiziert ins Prompt
memory_retain_node: NACH LLM-Call — extrahiert Fakten aus Response, speichert

Graceful: Wenn Memory Engine nicht verfuegbar → Nodes sind No-Ops.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.graph.state import AgentGraphState

logger = logging.getLogger(__name__)


async def memory_recall_node(state: AgentGraphState) -> dict[str, Any]:
    """VOR dem LLM-Call: relevante Memories holen und ins System-Prompt injizieren."""
    from agent.memory.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return {}

    # Letzte User-Message als Query
    user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                user_msg = content
                break

    if not user_msg:
        return {}

    try:
        from hindsight_api.engine.memory_engine import Budget
        from hindsight_api.models import RequestContext

        bank_id = get_bank_id(state.get("user_id", "default"))

        result = await engine.recall_async(
            bank_id=bank_id,
            query=user_msg[:500],  # Token-Budget: Query nicht zu lang
            fact_type=["world", "experience"],
            budget=Budget.MID,
            max_tokens=2000,
            request_context=RequestContext(),
        )

        if not result.results:
            return {}

        # Top-10 Memories ins System-Prompt injizieren
        memory_lines = []
        for fact in result.results[:10]:
            entities = f" [{', '.join(fact.entities)}]" if fact.entities else ""
            memory_lines.append(f"- {fact.text}{entities}")

        memory_text = "\n".join(memory_lines)
        current_prompt = state.get("system_prompt", "")

        logger.info("Recalled %d memories for user %s", len(result.results), bank_id)
        return {"system_prompt": f"{current_prompt}\n\n## Relevant Memories\n{memory_text}"}

    except Exception as e:
        logger.debug("Memory recall skipped: %s", e)
        return {}


async def memory_retain_node(state: AgentGraphState) -> dict[str, Any]:
    """NACH dem LLM-Call: Fakten aus Conversation extrahieren und speichern."""
    from agent.memory.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return {}

    response = state.get("final_response", "")
    if not response:
        return {}

    # Letzte User-Message fuer Kontext
    user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                user_msg = content[:500]
                break

    try:
        from hindsight_api.models import RequestContext

        bank_id = get_bank_id(state.get("user_id", "default"))
        thread_id = state.get("thread_id", "")

        await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[{
                "content": f"User asked: {user_msg}\nAgent responded: {response[:2000]}",
                "context": f"thread:{thread_id} role:{state.get('current_role', 'default')}",
            }],
            request_context=RequestContext(),
        )

        logger.info("Retained conversation for user %s (thread=%s)", bank_id, thread_id)

    except Exception as e:
        logger.debug("Memory retain skipped: %s", e)

    return {}
