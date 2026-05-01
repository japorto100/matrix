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
from agent.runtime_events import make_runtime_event
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

_MEMORY_RECALL_CUE_TERMS = (
    "remember",
    "recall",
    "previous",
    "previously",
    "earlier",
    "last week",
    "last month",
    "we discussed",
    "my ",
    "i said",
    "i prefer",
    "preference",
    "risk per trade",
    "allocation",
    "open positions",
)
_CURRENT_MARKET_QUERY_TERMS = (
    "current market",
    "live market",
    "latest market",
    "market sentiment",
    "current price",
    "current chart",
    "recent earnings",
    "this week",
    "this quarter",
    "today",
    "tomorrow",
    "news",
)
_NO_PERSONAL_MEMORY_CUE_TERMS = (
    "do not store",
    "don't store",
    "dont store",
    "do not save",
    "don't save",
    "dont save",
    "do not remember",
    "don't remember",
    "dont remember",
    "do not retain",
    "don't retain",
    "dont retain",
    "not store",
    "not save",
    "not remember",
    "not retain",
    "not personal memory",
    "no personal memory",
    "without storing",
    "without saving",
    "without memory",
)
_NON_PERSONAL_GROUNDING_CUE_TERMS = (
    "retrieve_context",
    "semantic_lookup",
    "source-grounded",
    "source grounded",
    "ground the term",
    "semantic definition",
)


def _memory_event(
    *,
    status: str,
    name: str,
    state: AgentGraphState,
    summary: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return make_runtime_event(
        kind="memory",  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        name=name,
        summary=summary,
        thread_id=str(state.get("thread_id", "") or ""),
        turn=int(state.get("iteration", 0) or 0),
        metadata=metadata or {},
    )


def _memory_retain_timeout_seconds() -> float:
    try:
        return max(1.0, float(os.environ.get("MEMORY_RETAIN_TIMEOUT_SEC", "20.0")))
    except ValueError:
        return 20.0


def _should_skip_memory_recall(user_msg: str) -> tuple[bool, str]:
    """Skip personal memory prefetch for pure current/live-market requests."""
    text = f" {user_msg.lower()} "
    if _has_no_personal_memory_cue(text):
        return True, "user_requested_no_personal_memory"
    if _has_non_personal_grounding_cue(text):
        return True, "non_personal_grounding_without_memory_cue"
    has_memory_cue = any(term in text for term in _MEMORY_RECALL_CUE_TERMS)
    has_current_market_cue = any(
        term in text for term in _CURRENT_MARKET_QUERY_TERMS
    )
    if has_current_market_cue and not has_memory_cue:
        return True, "current_market_without_personal_memory_cue"
    return False, ""


def _has_no_personal_memory_cue(text: str) -> bool:
    normalized = f" {text.lower()} "
    return any(term in normalized for term in _NO_PERSONAL_MEMORY_CUE_TERMS)


def _has_non_personal_grounding_cue(text: str) -> bool:
    normalized = f" {text.lower()} "
    if any(term in normalized for term in _MEMORY_RECALL_CUE_TERMS):
        return False
    return any(term in normalized for term in _NON_PERSONAL_GROUNDING_CUE_TERMS)


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
    document_id = str(getattr(fact, "document_id", "") or metadata.get("document_id") or "")
    chunk_id = str(getattr(fact, "chunk_id", "") or metadata.get("chunk_id") or "")
    source_refs = _memory_source_refs(metadata, document_id=document_id, chunk_id=chunk_id)
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
            or document_id
            or chunk_id
            or ""
        ),
        "sourceRefs": source_refs,
        "rawEvidenceRef": str(metadata.get("raw_evidence_ref") or ""),
        "operationLogId": str(metadata.get("operation_log_id") or ""),
        "diffRef": str(metadata.get("diff_ref") or ""),
        "threadId": str(metadata.get("thread_id") or ""),
        "sessionId": str(metadata.get("session_id") or ""),
        "roomId": str(metadata.get("room_id") or metadata.get("matrix_room_id") or ""),
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


def _memory_source_refs(
    metadata: dict[str, Any],
    *,
    document_id: str = "",
    chunk_id: str = "",
) -> list[str]:
    refs: list[str] = []
    for key in (
        "raw_evidence_ref",
        "provenance_ref",
        "source_ref",
        "citation_ref",
        "audit_event_id",
    ):
        value = metadata.get(key)
        if isinstance(value, (list, tuple, set)):
            candidates = [str(entry).strip() for entry in value]
        else:
            candidates = [str(value or "").strip()]
        for candidate in candidates:
            if candidate and candidate not in refs:
                refs.append(candidate)

    if document_id and chunk_id and "#" not in document_id:
        doc_ref = f"{document_id}#{chunk_id}"
        if doc_ref not in refs:
            refs.append(doc_ref)
    elif document_id and document_id not in refs:
        refs.append(document_id)
    return refs


def _context_ref_summaries(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for block in blocks:
        refs = [
            str(ref).strip()
            for ref in block.get("sourceRefs", [])
            if str(ref).strip()
        ]
        summary = {
            "id": str(block.get("id") or ""),
            "source_refs": refs,
            "raw_evidence_ref": str(block.get("rawEvidenceRef") or ""),
            "operation_log_id": str(block.get("operationLogId") or ""),
            "diff_ref": str(block.get("diffRef") or ""),
            "thread_id": str(block.get("threadId") or ""),
            "session_id": str(block.get("sessionId") or ""),
            "room_id": str(block.get("roomId") or ""),
            "source_layer": str(block.get("sourceLayer") or ""),
            "context_tier": str(block.get("contextTier") or ""),
        }
        summaries.append(summary)
    return summaries


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
    user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                user_msg = content
                break

    if not user_msg:
        return {}

    should_skip, skip_reason = _should_skip_memory_recall(user_msg)
    if should_skip:
        return {
            "context_blocks": [],
            "source_layer_counts": {},
            "degradation_flags": [],
            "runtime_events": [
                _memory_event(
                    status="blocked",
                    name="memory.recall.skipped",
                    state=state,
                    summary="Memory recall skipped by query policy",
                    metadata={
                        "source": "memory_recall_node",
                        "reason": skip_reason,
                    },
                )
            ],
            "query_gate": {
                "action": "skip",
                "reason": skip_reason,
                "needsVerification": False,
                "degradationFlags": [],
            },
        }

    from memory_fusion.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return {
            "degradation_flags": build_degradation_flags(
                source_layer_counts={},
                context_blocks=[],
            ),
            "runtime_events": [
                _memory_event(
                    status="blocked",
                    name="memory.recall.unavailable",
                    state=state,
                    summary="Memory recall skipped because no memory engine is available",
                    metadata={"source": "memory_recall_node"},
                )
            ],
        }

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
            context_ref_summaries = _context_ref_summaries(context_blocks)
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
                    "runtime_events": [
                        _memory_event(
                            status="completed",
                            name="memory.recall.completed",
                            state=state,
                            summary="Memory recall completed without selected context",
                            metadata={
                                "bank_id": bank_id,
                                "role": role,
                                "source": "memory_recall_node",
                                "facts_recalled": 0,
                                "entities": len(result.entities)
                                if result.entities
                                else 0,
                                "query_gate_action": query_gate.action,
                                "query_gate_reason": query_gate.reason,
                                "degradation_flags": degradation_flags
                                or ["NO_PERSONAL_MEMORY"],
                            },
                        )
                    ],
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

            runtime_event = _memory_event(
                status="completed",
                name="memory.recall.completed",
                state=state,
                summary="Memory recall selected context for prompt assembly",
                metadata={
                    "bank_id": bank_id,
                    "role": role,
                    "source": "memory_recall_node",
                    "facts_recalled": len(new_ids),
                    "entities": len(result.entities) if result.entities else 0,
                    "tokens_used": len(memory_text),
                    "source_layer_counts": source_layer_counts,
                    "query_gate_action": query_gate.action,
                    "query_gate_reason": query_gate.reason,
                    "degradation_flags": degradation_flags,
                    "context_refs": context_ref_summaries,
                },
            )
            await audit_log(
                action=AuditAction.MEMORY_RECALL,
                thread_id=thread_id,
                output_data=memory_text[:2000],
                success=True,
                metadata={
                    "bank_id": bank_id,
                    "role": role,
                    "source": "memory_recall_node",
                    "facts_recalled": len(new_ids),
                    "entities": len(result.entities) if result.entities else 0,
                    "tokens_used": len(memory_text),
                    "runtime_events": [runtime_event],
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
                "runtime_events": [runtime_event],
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
                ),
                "runtime_events": [
                    _memory_event(
                        status="failed",
                        name="memory.recall.failed",
                        state=state,
                        summary="Memory recall failed and was skipped",
                        metadata={
                            "source": "memory_recall_node",
                            "error": str(e),
                        },
                    )
                ],
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
    memory_write_policy = str(state.get("memory_write_policy") or "default")
    if (
        state.get("child_memory_write_allowed") is False
        or memory_write_policy in {"parent_only", "disabled", "none"}
    ):
        return {
            "runtime_events": [
                _memory_event(
                    status="blocked",
                    name="memory.retain.blocked",
                    state=state,
                    summary="Memory retain skipped because child runs cannot write durable shared memory",
                    metadata={
                        "reason": "child_memory_write_disabled",
                        "memory_write_policy": memory_write_policy,
                        "parent_thread_id": str(state.get("parent_thread_id") or ""),
                        "spawn_depth": state.get("spawn_depth", 0),
                    },
                )
            ]
        }

    role = state.get("current_role", "default")
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

    if _has_no_personal_memory_cue(user_msg) or _has_non_personal_grounding_cue(user_msg):
        reason = (
            "user_requested_no_personal_memory"
            if _has_no_personal_memory_cue(user_msg)
            else "non_personal_grounding_without_memory_cue"
        )
        return {
            "runtime_events": [
                _memory_event(
                    status="blocked",
                    name="memory.retain.blocked",
                    state=state,
                    summary="Memory retain skipped because the user requested no personal memory",
                    metadata={
                        "role": role,
                        "reason": reason,
                        "source": "memory_retain_node",
                    },
                )
            ]
        }

    from memory_fusion.engine import get_bank_id, get_memory_engine

    engine = await get_memory_engine()
    if engine is None:
        return {
            "runtime_events": [
                _memory_event(
                    status="blocked",
                    name="memory.retain.unavailable",
                    state=state,
                    summary="Memory retain skipped because no memory engine is available",
                    metadata={"source": "memory_retain_node"},
                )
            ]
        }

    mem_config = _get_memory_config(role)

    if not mem_config.get("memory_write", True):
        logger.debug("Memory retain skipped: role '%s' is read-only", role)
        return {
            "runtime_events": [
                _memory_event(
                    status="blocked",
                    name="memory.retain.blocked",
                    state=state,
                    summary="Memory retain skipped because role is read-only",
                    metadata={"role": role, "reason": "role_memory_write_disabled"},
                )
            ]
        }

    timeout_s = _memory_retain_timeout_seconds()
    try:
        retain_metadata = await asyncio.wait_for(
            _retain_conversation_memory(
                state=state,
                engine=engine,
                role=role,
                user_msg=user_msg,
                response=response,
            ),
            timeout=timeout_s,
        )
        return {
            "runtime_events": [
                _memory_event(
                    status="completed",
                    name="memory.retain.completed",
                    state=state,
                    summary="Memory retain completed",
                    metadata=retain_metadata,
                )
            ]
        }
    except TimeoutError:
        logger.warning(
            "Memory retain timed out after %.1fs (thread=%s)",
            timeout_s,
            state.get("thread_id", ""),
        )
        runtime_event = _memory_event(
            status="stale",
            name="memory.retain.timeout",
            state=state,
            summary="Memory retain timed out and turn continued",
            metadata={
                "role": role,
                "timeout_s": timeout_s,
                "source": "memory_retain_node",
            },
        )
        try:
            from agent.audit.logger import AuditAction, audit_log

            await audit_log(
                action=AuditAction.MEMORY_RETAIN,
                thread_id=state.get("thread_id", ""),
                input_data=f"User asked: {user_msg}\nAgent responded: {response[:2000]}",
                success=False,
                metadata={
                    "bank_id": get_bank_id(state.get("user_id", "default")),
                    "role": role,
                    "timeout_s": timeout_s,
                    "source": "memory_retain_node",
                    "error": f"memory retain timed out after {timeout_s:.1f}s",
                    "runtime_events": [runtime_event],
                },
            )
        except Exception:  # noqa: BLE001
            logger.debug("Memory retain timeout audit failed", exc_info=True)
        return {
            "runtime_events": [runtime_event],
            "degradation_flags": ["memory_retain_timeout"],
        }
    except Exception as e:
        logger.debug("Memory retain skipped: %s", e)
        return {
            "runtime_events": [
                _memory_event(
                    status="failed",
                    name="memory.retain.failed",
                    state=state,
                    summary="Memory retain failed and was skipped",
                    metadata={"role": role, "error": str(e)},
                )
            ]
        }

    return {}


async def _retain_conversation_memory(
    *,
    state: AgentGraphState,
    engine: Any,
    role: str,
    user_msg: str,
    response: str,
) -> dict[str, Any]:
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

        content_items = [
            {
                "content": content,
                "context": f"thread:{thread_id} role:{role}",
                "event_date": now,
                "tags": [role] if role != "default" else [],
                "metadata": {
                    "thread_id": thread_id,
                    "role": role,
                    "agent_class": state.get("agent_class", "advisory"),
                    "source": "automatic_memory_retain",
                },
                "document_id": f"{thread_id}:{role}:{now.strftime('%Y%m%d%H%M')}",
            }
        ]
        operation_context = {
            "thread_id": thread_id,
            "user_id": state.get("user_id", ""),
            "agent_id": state.get("agent_id", "default"),
            "actor_role": role,
        }
        document_tags = [role] if role != "default" else []
        storage_route = "fusion"
        storage_providers = "fusion"
        summary_status = "not_supported"
        try:
            await engine.retain_batch_async(
                bank_id=bank_id,
                contents=content_items,
                request_context=RequestContext(),
                document_tags=document_tags,
                consumer="agent_writer",
                operation_context=operation_context,
                route="verbatim",
            )
            storage_route = "verbatim"
            storage_providers = "verbatim,summary_async"
            summary_status = _queue_summary_retain(
                engine=engine,
                bank_id=bank_id,
                contents=content_items,
                document_tags=document_tags,
                operation_context=operation_context,
            )
        except TypeError:
            await engine.retain_batch_async(
                bank_id=bank_id,
                contents=content_items,
                request_context=RequestContext(),
                document_tags=document_tags,
                consumer="agent_writer",
                operation_context=operation_context,
            )

        span.set_attribute("memory.content_length", len(content))

        from agent.audit.logger import AuditAction, audit_log

        retain_metadata = {
            "bank_id": bank_id,
            "role": role,
            "content_length": len(content),
            "conflict": conflict.has_conflict if conflict else False,
            "route": storage_route,
            "provider": "fusion",
            "providers": storage_providers,
            "source": "automatic_memory_retain",
            "summary_status": summary_status,
        }
        runtime_event = _memory_event(
            status="completed",
            name="memory.retain.completed",
            state=state,
            summary="Memory retain completed",
            metadata=retain_metadata,
        )

        await audit_log(
            action=AuditAction.MEMORY_RETAIN,
            thread_id=thread_id,
            input_data=content[:2000],
            success=True,
            metadata={**retain_metadata, "runtime_events": [runtime_event]},
        )

        logger.info(
            "Retained conversation for %s (role=%s, thread=%s)",
            bank_id,
            role,
            thread_id,
        )
        return retain_metadata


def _queue_summary_retain(
    *,
    engine: Any,
    bank_id: str,
    contents: list[dict[str, Any]],
    document_tags: list[str],
    operation_context: dict[str, Any],
) -> str:
    submit_async = getattr(engine, "submit_async_retain", None)
    if not callable(submit_async):
        return "not_supported"

    async def _submit() -> None:
        try:
            from hindsight_api.models import RequestContext

            await submit_async(
                bank_id,
                contents,
                request_context=RequestContext(),
                document_tags=document_tags,
                consumer="agent_writer",
                operation_context=operation_context,
                route="summary",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("automatic memory summary retain failed: %s", exc)

    try:
        asyncio.create_task(_submit())
        return "background_queued"
    except Exception:
        return "background_dispatch_failed"
