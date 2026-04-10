"""Memory Nodes — Recall + Retain als LangGraph Nodes (exec-11).

memory_recall_node: VOR LLM-Call — holt relevante Memories, injiziert ins Prompt
memory_retain_node: NACH LLM-Call — extrahiert Fakten aus Response, speichert

SOTA Coverage (Papers 2,3,5):
  - Quality Gates: Hindsight built-in (coreference, self-containment, temporal anchor)
  - Entity Isolation: Tag-based scoping via roles.py TRADING_ROLE_MEMORY
  - Multi-Graph: Hindsight 4 Link-Typen + 4 Retrieval-Strategien (MAGMA Pattern)
  - Governed Retrieval: include_entities + observation facts
  - Progressive Context: tracked via _injected_context (session-aware)

Graceful: Wenn Memory Engine nicht verfuegbar → Nodes sind No-Ops.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from agent.graph.state import AgentGraphState
from agent.roles import TRADING_ROLE_MEMORY

logger = logging.getLogger(__name__)

# Progressive Context: trackt was schon injiziert wurde pro Thread (Paper 3 Pattern)
_injected_context: dict[str, set[str]] = {}


def _get_memory_config(role: str) -> dict:
    """Holt Memory-Config fuer eine Rolle aus roles.py (zentral)."""
    for r, config in TRADING_ROLE_MEMORY.items():
        if r.value == role:
            return config
    return {"memory_write": True, "memory_recall_tags": None}


async def memory_recall_node(state: AgentGraphState) -> dict[str, Any]:
    """VOR dem LLM-Call: relevante Memories holen und ins System-Prompt injizieren.

    Nutzt volle Hindsight API:
    - fact_type: world + experience + observation (consolidated knowledge)
    - include_entities: Entity observations
    - question_date: temporale Relevanz
    - tags: Rollen-basiert aus roles.py
    - Progressive Context: Duplikat-Memories nicht nochmal injizieren
    """
    from agent.memory.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return {}

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
        role = state.get("current_role", "default")
        thread_id = state.get("thread_id", "")
        mem_config = _get_memory_config(role)
        recall_tags = mem_config.get("memory_recall_tags")

        kwargs: dict[str, Any] = {
            "bank_id": bank_id,
            "query": user_msg[:500],
            "fact_type": ["world", "experience", "observation"],
            "budget": Budget.MID,
            "max_tokens": 2000,
            "include_entities": True,
            "max_entity_tokens": 500,
            "question_date": datetime.now(UTC),
            "request_context": RequestContext(),
        }
        if recall_tags is not None:
            kwargs["tags"] = recall_tags

        result = await engine.recall_async(**kwargs)

        if not result.results:
            return {}

        # Progressive Context: nur neue Memories injizieren (Paper 3 Pattern)
        thread_key = f"{thread_id}:{role}"
        already_seen = _injected_context.get(thread_key, set())

        memory_lines = []
        new_ids = set()
        for fact in result.results[:10]:
            if fact.id in already_seen:
                continue
            new_ids.add(fact.id)
            entities = f" [{', '.join(fact.entities)}]" if fact.entities else ""
            tags_str = f" #{','.join(fact.tags)}" if fact.tags else ""
            type_badge = f"[{fact.fact_type}] " if fact.fact_type == "observation" else ""
            memory_lines.append(f"- {type_badge}{fact.text}{entities}{tags_str}")

        # Entity observations
        if result.entities:
            for name, entity_state in list(result.entities.items())[:5]:
                if hasattr(entity_state, 'observations') and entity_state.observations:
                    for obs in entity_state.observations[:2]:
                        memory_lines.append(f"- [entity:{name}] {obs.text}")

        # Track injected IDs (Progressive Context)
        _injected_context[thread_key] = already_seen | new_ids

        if not memory_lines:
            return {}

        memory_text = "\n".join(memory_lines)
        current_prompt = state.get("system_prompt", "")

        logger.info("Recalled %d new memories + %d entities for %s (role=%s, %d skipped as already injected)",
                    len(new_ids),
                    len(result.entities) if result.entities else 0,
                    bank_id, role,
                    len(already_seen & {f.id for f in result.results[:10]}))
        return {"system_prompt": f"{current_prompt}\n\n## Relevant Memories\n{memory_text}"}

    except Exception as e:
        logger.debug("Memory recall skipped: %s", e)
        return {}


async def memory_retain_node(state: AgentGraphState) -> dict[str, Any]:
    """NACH dem LLM-Call: Fakten aus Conversation extrahieren und speichern.

    Nutzt volle Hindsight API:
    - event_date: Zeitstempel
    - metadata: thread_id, role, agent_class
    - document_id: Upsert-Key (dedupliziert bei Re-Runs)
    - tags: Rollen-Tag fuer Memory Sharing Sichtbarkeit
    - observation_scopes: Scoped Consolidation

    Quality Gates: Hindsight built-in (coreference, self-containment, temporal).
    Read-only Rollen retainen nicht.
    """
    from agent.memory.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return {}

    role = state.get("current_role", "default")
    mem_config = _get_memory_config(role)

    if not mem_config.get("memory_write", True):
        logger.debug("Memory retain skipped: role '%s' is read-only", role)
        return {}

    response = state.get("final_response", "")
    if not response:
        return {}

    user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                user_msg = content[:500]
                break

    try:
        from hindsight_api.models import RequestContext

        from agent.memory.coherence import get_coherence_manager

        bank_id = get_bank_id(state.get("user_id", "default"))
        thread_id = state.get("thread_id", "")
        now = datetime.now(UTC)
        content = f"User asked: {user_msg}\nAgent responded: {response[:2000]}"

        # Cache Coherence: Write-Ahead Log + Conflict Detection
        coherence = get_coherence_manager()
        await coherence.write_ahead(bank_id, role, content, tags=[role] if role != "default" else [])
        conflict = await coherence.detect_conflicts(bank_id)
        if conflict.has_conflict:
            logger.info("Memory conflict detected: %d entries from %d roles in bank %s",
                       len(conflict.entries), len({e.role for e in conflict.entries}), bank_id)

        await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[{
                "content": content,
                "context": f"thread:{thread_id} role:{role}",
                "event_date": now,
                "tags": [role] if role != "default" else [],
                "metadata": {
                    "thread_id": thread_id,
                    "role": role,
                    "agent_class": state.get("agent_class", "advisory"),
                },
                "document_id": f"{thread_id}:{role}:{now.strftime('%Y%m%d%H%M')}",
            }],
            request_context=RequestContext(),
            document_tags=[role] if role != "default" else [],
        )

        logger.info("Retained conversation for %s (role=%s, thread=%s)", bank_id, role, thread_id)

    except Exception as e:
        logger.debug("Memory retain skipped: %s", e)

    return {}
