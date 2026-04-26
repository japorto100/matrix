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

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from agent.graph.state import AgentGraphState
from agent.roles import TRADING_ROLE_MEMORY
from context.policy import (
    LAYER_LABELS,
    apply_context_policy,
    build_degradation_flags,
    get_context_policy,
)
from memory_fusion.decay import derive_decay_metadata
from memory_fusion.query_gate import decide_query_path
from memory_fusion.semantics import (
    enrich_metadata_with_semantics,
)

logger = logging.getLogger(__name__)

# Progressive Context: trackt was schon injiziert wurde pro Thread (Paper 3 Pattern)
_injected_context: dict[str, set[str]] = {}


def _memory_retain_timeout_seconds() -> float:
    try:
        return max(1.0, float(os.environ.get("MEMORY_RETAIN_TIMEOUT_SEC", "20.0")))
    except ValueError:
        return 20.0


def _get_memory_config(role: str) -> dict:
    """Holt Memory-Config fuer eine Rolle aus roles.py (zentral)."""
    for r, config in TRADING_ROLE_MEMORY.items():
        if r.value == role:
            return config
    return {"memory_write": True, "memory_recall_tags": None}


def _block_from_fact(fact: Any, *, fallback_id: int) -> dict[str, Any]:
    metadata = enrich_metadata_with_semantics(
        derive_decay_metadata(dict(getattr(fact, "metadata", {}) or {})),
        fact_type=str(getattr(fact, "fact_type", "") or ""),
    )
    text = str(getattr(fact, "text", "") or "")
    return {
        "id": str(getattr(fact, "id", "") or fallback_id),
        "title": str(
            metadata.get("artifact_type")
            or getattr(fact, "fact_type", "")
            or "memory item"
        ).replace("_", " ").title(),
        "preview": text[:240] + ("..." if len(text) > 240 else ""),
        "sourceLayer": str(metadata.get("memory_layer") or "unknown"),
        "sourceType": str(metadata.get("source_type") or "unknown"),
        "artifactType": str(metadata.get("artifact_type") or "unknown"),
        "groundingStatus": str(metadata.get("grounding_status") or "unknown"),
        "promotionStatus": str(metadata.get("promotion_status") or "not_applicable"),
        "provenanceRef": str(
            metadata.get("provenance_ref")
            or metadata.get("source_ref")
            or metadata.get("document_id")
            or metadata.get("chunk_id")
            or ""
        ),
        "sourceConfidence": metadata.get("source_confidence"),
        "actorRole": str(metadata.get("actor_role") or "unknown"),
        "status": str(metadata.get("status") or "available"),
        "freshness": metadata.get("freshness_score") or metadata.get("freshness"),
        "supportCount": metadata.get("support_count"),
        "conflictCount": metadata.get("conflict_count"),
        "factType": str(getattr(fact, "fact_type", "") or metadata.get("fact_type") or ""),
        "route": str(metadata.get("fusion_route") or ""),
        "tokenCount": max(1, len(text.split())) if text.strip() else 0,
    }


def _format_prompt_line(block: dict[str, Any], fact: Any) -> str:
    text = str(getattr(fact, "text", "") or "").strip() or str(block.get("preview") or "").strip()
    entities = f" [{', '.join(getattr(fact, 'entities', []) or [])}]" if getattr(fact, "entities", None) else ""
    tags = list(getattr(fact, "tags", []) or [])
    tags_str = f" #{','.join(tags)}" if tags else ""

    provenance = str(block.get("provenanceRef") or "").strip()
    status = str(block.get("status") or "").strip()
    if provenance and status:
        return f"- [{status}] {text}{entities}{tags_str} ({provenance})"
    if provenance:
        return f"- {text}{entities}{tags_str} ({provenance})"
    return f"- {text}{entities}{tags_str}"


def _format_prompt_sections(blocks: list[dict[str, Any]], facts_by_id: dict[str, Any]) -> str:
    grouped: dict[str, list[str]] = {}
    for block in blocks:
        fact = facts_by_id.get(str(block.get("id") or ""))
        if fact is None:
            continue
        layer = str(block.get("sourceLayer") or "unknown")
        grouped.setdefault(layer, []).append(_format_prompt_line(block, fact))

    lines: list[str] = []
    for layer, label in LAYER_LABELS.items():
        section_lines = grouped.get(layer, [])
        if not section_lines:
            continue
        lines.append(f"### {label}")
        lines.extend(section_lines)
    return "\n".join(lines).strip()


async def memory_recall_node(state: AgentGraphState) -> dict[str, Any]:
    """VOR dem LLM-Call: relevante Memories holen und ins System-Prompt injizieren.

    Nutzt volle Hindsight API:
    - fact_type: world + experience + observation (consolidated knowledge)
    - include_entities: Entity observations
    - question_date: temporale Relevanz
    - tags: Rollen-basiert aus roles.py
    - Progressive Context: Duplikat-Memories nicht nochmal injizieren
    """
    from memory_fusion.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return {
            "degradation_flags": build_degradation_flags(
                source_layer_counts={},
                context_blocks=[],
            )
        }

    user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                user_msg = content
                break

    if not user_msg:
        return {}

    from agent.tracing import memory_span

    with memory_span("hindsight_recall", user_msg[:200]) as span:
        try:
            from hindsight_api.engine.memory_engine import Budget
            from hindsight_api.models import RequestContext

            bank_id = get_bank_id(state.get("user_id", "default"))
            role = state.get("current_role", "default")
            thread_id = state.get("thread_id", "")
            mem_config = _get_memory_config(role)
            recall_tags = mem_config.get("memory_recall_tags")
            policy = get_context_policy("llm_agent")
            query_gate = decide_query_path(user_msg[:500], engine._normalize_query(user_msg[:500]))

            kwargs: dict[str, Any] = {
                "bank_id": bank_id,
                "query": user_msg[:500],
                "fact_type": list(policy.recall_fact_types),
                "budget": Budget.MID,
                "max_tokens": 2000,
                "include_entities": True,
                "max_entity_tokens": 500,
                "question_date": datetime.now(UTC),
                "request_context": RequestContext(),
                "consumer": "llm_agent",
                "operation_context": {
                    "thread_id": thread_id,
                    "user_id": state.get("user_id", ""),
                    "agent_id": state.get("agent_id", "default"),
                    "actor_role": role,
                },
            }
            if recall_tags is not None:
                kwargs["tags"] = recall_tags

            result = await engine.recall_async(**kwargs)

            # Progressive Context: nur neue Memories injizieren (Paper 3 Pattern)
            thread_key = f"{thread_id}:{role}"
            already_seen = _injected_context.get(thread_key, set())

            raw_blocks: list[dict[str, Any]] = []
            facts_by_id: dict[str, Any] = {}
            for idx, fact in enumerate(result.results[:10]):
                if fact.id in already_seen:
                    continue
                block = _block_from_fact(fact, fallback_id=idx)
                raw_blocks.append(block)
                facts_by_id[str(block["id"])] = fact

            context_blocks, source_layer_counts, degradation_flags = apply_context_policy(
                raw_blocks,
                consumer="llm_agent",
            )
            degradation_flags = list(degradation_flags)
            for flag in query_gate.degradation_flags:
                if flag not in degradation_flags:
                    degradation_flags.append(flag)
            memory_text = _format_prompt_sections(context_blocks, facts_by_id)
            new_ids = {
                str(block.get("id") or "")
                for block in context_blocks
                if str(block.get("id") or "").strip()
            }

            # Entity observations
            entity_lines: list[str] = []
            if result.entities:
                for name, entity_state in list(result.entities.items())[:5]:
                    if (
                        hasattr(entity_state, "observations")
                        and entity_state.observations
                    ):
                        for obs in entity_state.observations[:2]:
                            entity_lines.append(f"- [entity:{name}] {obs.text}")

            if entity_lines:
                entity_section = "### Entity Observations\n" + "\n".join(entity_lines)
                memory_text = f"{memory_text}\n\n{entity_section}".strip()

            if not memory_text:
                span.set_attribute("memory.results", 0)
                return {
                    "context_blocks": [],
                    "source_layer_counts": {},
                    "degradation_flags": degradation_flags or ["NO_PERSONAL_MEMORY"],
                    "query_gate": {
                        "action": query_gate.action,
                        "reason": query_gate.reason,
                        "needsVerification": query_gate.needs_verification,
                        "degradationFlags": list(query_gate.degradation_flags),
                    },
                }

            # Track injected IDs (Progressive Context)
            _injected_context[thread_key] = already_seen | new_ids

            current_prompt = state.get("system_prompt", "")

            span.set_attribute("memory.results", len(new_ids))
            span.set_attribute(
                "memory.entities", len(result.entities) if result.entities else 0
            )
            span.set_attribute("memory.tokens_used", len(memory_text))

            from agent.audit.logger import AuditAction, audit_log

            await audit_log(
                action=AuditAction.MEMORY_RECALL,
                thread_id=thread_id,
                output_data=memory_text[:2000],
                success=True,
                metadata={
                    "bank_id": bank_id,
                    "role": role,
                    "facts_recalled": len(new_ids),
                    "entities": len(result.entities) if result.entities else 0,
                    "tokens_used": len(memory_text),
                },
            )

            logger.info(
                "Recalled %d new memories + %d entities for %s (role=%s, %d skipped as already injected)",
                len(new_ids),
                len(result.entities) if result.entities else 0,
                bank_id,
                role,
                len(already_seen & {f.id for f in result.results[:10]}),
            )
            return {
                "system_prompt": f"{current_prompt}\n\n## Relevant Context\n{memory_text}",
                "context_blocks": context_blocks,
                "source_layer_counts": source_layer_counts,
                "degradation_flags": degradation_flags,
                "query_gate": {
                    "action": query_gate.action,
                    "reason": query_gate.reason,
                    "needsVerification": query_gate.needs_verification,
                    "degradationFlags": list(query_gate.degradation_flags),
                },
            }

        except Exception as e:
            logger.debug("Memory recall skipped: %s", e)
            return {
                "degradation_flags": build_degradation_flags(
                    source_layer_counts={},
                    context_blocks=[],
                )
            }


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
    from memory_fusion.engine import get_bank_id, get_memory_engine

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

    timeout_s = _memory_retain_timeout_seconds()
    try:
        await asyncio.wait_for(
            _retain_conversation_memory(
                state=state,
                engine=engine,
                role=role,
                user_msg=user_msg,
                response=response,
            ),
            timeout=timeout_s,
        )
    except TimeoutError:
        logger.warning(
            "Memory retain timed out after %.1fs (thread=%s)",
            timeout_s,
            state.get("thread_id", ""),
        )
        try:
            from agent.audit.logger import AuditAction, audit_log

            await audit_log(
                action=AuditAction.MEMORY_RETAIN,
                thread_id=state.get("thread_id", ""),
                input_data=f"User asked: {user_msg}\nAgent responded: {response[:2000]}",
                success=False,
                error=f"memory retain timed out after {timeout_s:.1f}s",
                metadata={
                    "bank_id": get_bank_id(state.get("user_id", "default")),
                    "role": role,
                    "timeout_s": timeout_s,
                    "source": "memory_retain_node",
                },
            )
        except Exception:  # noqa: BLE001
            logger.debug("Memory retain timeout audit failed", exc_info=True)
    except Exception as e:
        logger.debug("Memory retain skipped: %s", e)

    return {}


async def _retain_conversation_memory(
    *,
    state: AgentGraphState,
    engine: Any,
    role: str,
    user_msg: str,
    response: str,
) -> None:
    from hindsight_api.models import RequestContext

    from agent.tracing import memory_span
    from memory_fusion.coherence import get_coherence_manager
    from memory_fusion.engine import get_bank_id

    with memory_span("hindsight_retain", user_msg[:200]) as span:
        bank_id = get_bank_id(state.get("user_id", "default"))
        thread_id = state.get("thread_id", "")
        now = datetime.now(UTC)
        content = f"User asked: {user_msg}\nAgent responded: {response[:2000]}"

        # Cache Coherence: Write-Ahead Log + Conflict Detection
        coherence = get_coherence_manager()
        await coherence.write_ahead(
            bank_id, role, content, tags=[role] if role != "default" else []
        )
        conflict = await coherence.detect_conflicts(bank_id)
        if conflict.has_conflict:
            span.set_attribute("memory.conflict", True)
            logger.info(
                "Memory conflict detected: %d entries from %d roles in bank %s",
                len(conflict.entries),
                len({e.role for e in conflict.entries}),
                bank_id,
            )

        await engine.retain_batch_async(
            bank_id=bank_id,
            contents=[
                {
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
                }
            ],
            request_context=RequestContext(),
            document_tags=[role] if role != "default" else [],
            consumer="agent_writer",
            operation_context={
                "thread_id": thread_id,
                "user_id": state.get("user_id", ""),
                "agent_id": state.get("agent_id", "default"),
                "actor_role": role,
            },
        )

        span.set_attribute("memory.content_length", len(content))

        from agent.audit.logger import AuditAction, audit_log

        await audit_log(
            action=AuditAction.MEMORY_RETAIN,
            thread_id=thread_id,
            input_data=content[:2000],
            success=True,
            metadata={
                "bank_id": bank_id,
                "role": role,
                "content_length": len(content),
                "conflict": conflict.has_conflict if conflict else False,
            },
        )

        logger.info(
            "Retained conversation for %s (role=%s, thread=%s)",
            bank_id,
            role,
            thread_id,
        )
