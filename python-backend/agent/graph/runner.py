# Agent Graph Runner — exec-12 refactor (was agent/loop.py)
# Entry point: run_agent_loop() → pre-processing → LangGraph execution → SSE stream.
# Legacy manual while-loop removed — LangGraph is the only execution path.

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from agent.context import AgentExecutionContext
from agent.graph.agent_graph import MAX_ITERATIONS, create_agent_graph
from agent.streaming import (
    FinishPacket,
    MessageMetaPacket,
    StartPacket,
    StepStartPacket,
    TextDeltaPacket,
    TextEndPacket,
    TextStartPacket,
    ToolErrorPacket,
    ToolResultPacket,
    ToolStartPacket,
    sse,
)

logger = logging.getLogger(__name__)


TOOL_INSTRUCTION_PROMPT = """
## Tool Instruction Compliance

When the user explicitly asks you to use a named available tool, call that tool
before answering. Do not answer from memory or a prior result instead.

- If the user says `use memory_search`, call `memory_search`.
- If the user says `use memory_add` or asks you to remember something long-term,
  call `memory_add`.
- Use `save_memory` only for short-lived thread scratchpad notes, not persistent
  project memory or evidence.
"""


# exec-hermes Phase-B P4: LiteLLM model_metadata wrapper. The hardcoded
# dict and _fallback_model_max_tokens helper have been removed in favour
# of the TTL-cached LiteLLM lookup.


def _float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        return default


async def run_agent_loop(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Agent entry point — pre-processing → LangGraph → SSE stream.

    Yields SSE strings (Vercel AI Data Stream Protocol).
    Called from agent/app.py via _stream_agent_loop().
    """
    # ACR-G7: AI-SDK v6 requires `start` as first packet. Thread-id flows
    # through start.messageId + a follow-up message-metadata for explicit
    # access on the frontend.
    yield sse(StartPacket(message_id=ctx.thread_id))
    yield sse(MessageMetaPacket(message_metadata={"threadId": ctx.thread_id}))

    # Pre-processing: Skills, Temporal Context, Summarization, Dangling Tool
    # Calls. Each sub-step hits the DB or HuggingFace hub — a single stuck
    # call would otherwise hang the SSE stream indefinitely. We wrap both
    # pre-processing phases in a per-phase timeout and fall back to a plain
    # system_prompt / untouched messages when they time out. The stream
    # thereby proceeds even when hindsight/memory are saturated.
    try:
        system_prompt = await asyncio.wait_for(
            _prepare_system_prompt(ctx, messages), timeout=12.0
        )
    except TimeoutError:
        logger.warning("_prepare_system_prompt timed out — using bare prompt")
        system_prompt = ctx.system_prompt
    try:
        messages = await asyncio.wait_for(
            _prepare_messages(messages, ctx), timeout=8.0
        )
    except TimeoutError:
        logger.warning("_prepare_messages timed out — using raw messages")

    # Run LangGraph
    async for chunk in _run_graph(ctx, messages, system_prompt):
        yield chunk


def _last_user_text(msgs: list[dict]) -> str:
    for msg in reversed(msgs):
        if isinstance(msg, dict) and msg.get("role") == "user":
            c = msg.get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                parts = []
                for block in c:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                return " ".join(parts)
    return ""


def _memory_bank_id_for_user(user_id: str | None) -> str | None:
    if not user_id:
        return None
    from memory_fusion.engine import get_bank_id

    return get_bank_id(user_id)


async def _prepare_system_prompt(
    ctx: AgentExecutionContext, messages: list[dict]
) -> str:
    """Enrich system prompt with skills, temporal context, and security instructions."""
    from agent.middleware.sanitizer import SYSTEM_PROMPT_INJECTION
    from agent.tracing import turn_span

    with turn_span("prepare_system_prompt", "", 0) as span:
        system_prompt = ctx.system_prompt + SYSTEM_PROMPT_INJECTION
        system_prompt = f"{system_prompt}\n\n{TOOL_INSTRUCTION_PROMPT.strip()}"

        # exec-10 + exec-skills Phase 1: Skill Injection (finder wenn User-Query vorhanden)
        try:
            from agent.skills.loader import format_skills_for_prompt_async

            skill_query = _last_user_text(messages)
            skills_text = await asyncio.wait_for(
                format_skills_for_prompt_async(
                    None,
                    query=skill_query or None,
                    user_id=ctx.user_id,
                    context_hint=ctx.system_prompt[:800],
                    api_key=ctx.api_key,
                    session_id=ctx.thread_id,
                    thread_id=ctx.thread_id,
                ),
                timeout=max(0.2, _float_env("AGENT_SKILL_PROMPT_TIMEOUT_S", 4.0)),
            )
            if skills_text:
                system_prompt = f"{system_prompt}\n\n{skills_text}"
        except TimeoutError:
            logger.warning("skill prompt injection timed out — continuing without skills")
        except Exception:
            pass

        # exec-10 Phase 3.5: Temporal Context
        try:
            from agent.temporal_context import get_temporal_context

            temporal = get_temporal_context(user_id=ctx.user_id)
            if temporal:
                system_prompt = f"{system_prompt}\n\n{temporal}"
        except Exception:
            pass

        # Feature 009: per-user agent settings. This is a fail-soft prompt
        # surface; hard enforcement remains in tool permissions, skill toggles
        # and memory/context policy.
        try:
            from agent.security.agent_settings import get_user_agent_settings

            agent_id = getattr(ctx, "agent_id", "default") or "default"
            settings = await get_user_agent_settings(ctx.user_id, agent_id=agent_id)
            if settings is not None:
                system_prompt = f"{system_prompt}\n\n{settings.prompt_block()}"
                span.set_attribute("agent.settings.memory_scope", settings.memory_scope)
                span.set_attribute("agent.settings.enabled_skills", len(settings.enabled_skills))
                span.set_attribute("agent.settings.tool_allowlist", len(settings.tool_allowlist))
        except Exception:  # noqa: BLE001
            logger.debug("User agent settings skipped", exc_info=True)

        # exec-hermes Phase-B P1: Memory recall via MemoryManager (new path)
        # with Hindsight-direct (legacy path) as fallback. MemoryManager is
        # None until init_stack seeds it — callers must handle that case.
        memory_injected = False
        try:
            from memory_fusion.memory_provider import get_memory_manager

            manager = get_memory_manager()
            if manager is not None:
                # Static provider blocks (always present regardless of query)
                blocks = manager.system_prompt_blocks()
                for block in blocks:
                    if block:
                        system_prompt = f"{system_prompt}\n\n{block}"

                # Dynamic prefetch (query-based recall)
                user_query = _last_user_text(messages) or ctx.system_prompt[:200]

                recalls = await asyncio.wait_for(
                    manager.prefetch(
                        user_query,
                        user_id=ctx.user_id,
                        bank_id=_memory_bank_id_for_user(ctx.user_id) or "",
                        limit_per_provider=5,
                    ),
                    timeout=max(
                        0.2,
                        _float_env("AGENT_PROMPT_MEMORY_PREFETCH_TIMEOUT_S", 3.0),
                    ),
                )
                if recalls:
                    mem_lines = [f"- {r.content}" for r in recalls[:8] if r.content]
                    if mem_lines:
                        system_prompt = (
                            f"{system_prompt}\n\n## Relevant Memories\n"
                            + "\n".join(mem_lines)
                        )
                memory_injected = True
                span.set_attribute(
                    "memory.manager.providers", len(manager.providers)
                )
                span.set_attribute("memory.manager.recalls", len(recalls))
        except Exception:  # noqa: BLE001 — memory path mustn't break the turn
            logger.debug("MemoryManager prefetch skipped", exc_info=True)

        # exec-11 LEGACY fallback — MemoryManager not yet seeded (or failed)
        # → fall through to direct Hindsight recall. Once MemoryManager
        # reaches production stability this block can be deleted; P1 keeps
        # both paths to guarantee no regression during rollout.
        if not memory_injected:
            try:
                from memory_fusion.engine import get_bank_id, get_memory_engine

                engine = await asyncio.wait_for(
                    get_memory_engine(),
                    timeout=max(
                        0.2,
                        _float_env("AGENT_PROMPT_MEMORY_INIT_TIMEOUT_S", 2.0),
                    ),
                )
                if engine:
                    from hindsight_api.engine.memory_engine import Budget
                    from hindsight_api.models import RequestContext

                    bank_id = get_bank_id(ctx.user_id)
                    user_query = ""
                    for msg in reversed(getattr(ctx, "_messages", [])):
                        if isinstance(msg, dict) and msg.get("role") == "user":
                            user_query = str(msg.get("content", ""))[:300]
                            break
                    if not user_query:
                        user_query = ctx.system_prompt[:200]
                    result = await asyncio.wait_for(
                        engine.recall_async(
                            bank_id=bank_id,
                            query=user_query,
                            fact_type=["world", "experience", "observation"],
                            budget=Budget.MID,
                            max_tokens=1500,
                            request_context=RequestContext(),
                            consumer="llm_agent",
                            operation_context={
                                "thread_id": ctx.thread_id,
                                "user_id": ctx.user_id,
                                "agent_id": getattr(ctx, "agent_id", "default"),
                                "actor_role": getattr(ctx, "agent_class", "advisory"),
                            },
                        ),
                        timeout=max(
                            0.2,
                            _float_env("AGENT_PROMPT_MEMORY_RECALL_TIMEOUT_S", 3.0),
                        ),
                    )
                    if result.results:
                        mem_lines = [f"- {f.text}" for f in result.results[:8]]
                        system_prompt = (
                            f"{system_prompt}\n\n## Relevant Memories\n"
                            + "\n".join(mem_lines)
                        )
                    span.set_attribute("memory.fallback.hindsight_recall", True)
            except Exception:
                pass

        span.set_attribute("prompt.length", len(system_prompt))
        return system_prompt


async def _prepare_messages(
    messages: list[dict], ctx: AgentExecutionContext
) -> list[dict]:
    """Apply middleware to messages before graph execution."""
    from agent.tracing import turn_span

    def _memory_bank_id() -> str:
        return _memory_bank_id_for_user(ctx.user_id) or ""

    with turn_span("prepare_messages", ctx.model, 0) as span:
        # exec-hermes Phase-B P1 + P5: ContextEngine classifies + routes.
        # P1 emitted the stage as observability; P5 uses it to dispatch
        # between compaction (mechanical, cheap) and compression (LLM,
        # lossy, pre_compression event).
        stage_value = "normal"
        stage = None
        context_stage_cls = None
        try:
            from agent.llm.model_metadata import get_model_context_window
            from agent.middleware.compaction import estimate_tokens
            from context.context_engine import ContextStage, get_context_engine

            context_stage_cls = ContextStage
            engine = get_context_engine()
            est_tokens = estimate_tokens(messages)
            window = get_model_context_window(ctx.model)
            stage = engine.stage_for(tokens=est_tokens, window=window)
            stage_value = stage.value
            span.set_attribute("context.stage", stage_value)
            span.set_attribute("context.estimated_tokens", est_tokens)
            span.set_attribute("context.window", window)
        except Exception:  # noqa: BLE001 — observability mustn't break the turn
            logger.debug("ContextEngine.stage_for skipped", exc_info=True)

        # P5 router — lifecycle contract per exec-context §6.3:
        #   normal      → no-op
        #   pre_save    → archive current context, do not mutate prompt
        #   compaction  → archive, then mechanical compact()
        #   emergency   → compress() with bounded pre_compression hook
        try:
            if stage is not None and context_stage_cls is not None:
                from agent.middleware.compaction import compact
                from agent.middleware.compression import (
                    compress,
                    notify_pre_compression,
                )

                if stage is context_stage_cls.emergency:
                    span.add_event(
                        "pre_compression",
                        {"messages_count": len(messages), "context.stage": stage_value},
                    )
                    messages = await compress(
                        messages,
                        user_id=getattr(ctx, "user_id", None),
                        bank_id=getattr(ctx, "bank_id", None) or _memory_bank_id(),
                    )
                elif stage is context_stage_cls.compaction:
                    span.add_event(
                        "pre_compaction_archive",
                        {"messages_count": len(messages), "context.stage": stage_value},
                    )
                    await notify_pre_compression(
                        messages,
                        user_id=getattr(ctx, "user_id", None),
                        bank_id=getattr(ctx, "bank_id", None) or _memory_bank_id(),
                    )
                    messages = compact(messages)
                elif stage is context_stage_cls.pre_save:
                    span.add_event(
                        "pre_save_archive",
                        {"messages_count": len(messages), "context.stage": stage_value},
                    )
                    await notify_pre_compression(
                        messages,
                        user_id=getattr(ctx, "user_id", None),
                        bank_id=getattr(ctx, "bank_id", None) or _memory_bank_id(),
                    )
            else:
                # Fall-back path when ContextEngine is unavailable — retain
                # legacy unconditional pipeline for correctness.
                from agent.middleware.summarization import apply_context_management

                messages = await apply_context_management(messages, model=ctx.model)
        except Exception:
            logger.debug("context-management skipped", exc_info=True)

        # exec-10 Phase 5.1: Dangling Tool Calls patchen
        try:
            from agent.middleware.dangling_tool_call import patch_dangling_tool_calls

            messages = patch_dangling_tool_calls(messages)
        except Exception:
            pass

        return messages


async def _run_graph(
    ctx: AgentExecutionContext,
    messages: list[dict],
    system_prompt: str,
) -> AsyncGenerator[str, None]:
    """Execute the LangGraph agent and stream SSE events."""
    from agent.graph.state import AgentGraphState

    # exec-16: Model + Key aus Context (resolved in app.py via credentials).
    # Per-Rolle Routing: role override hat Vorrang vor default model.
    model = ctx.model
    try:
        from agent.security.credentials import get_user_role_model

        role_model = await get_user_role_model(ctx.user_id, "default")
        if role_model:
            model = role_model
    except Exception:
        pass

    graph = create_agent_graph()

    initial_state: AgentGraphState = {
        "messages": messages,
        "tool_calls": [],
        "tool_definitions": [tool.definition() for tool in ctx.tools],
        "tool_results": [],
        "iteration": 0,
        "max_iterations": MAX_ITERATIONS,
        "current_role": "default",
        "system_prompt": system_prompt,
        "model": model,
        "api_key": ctx.api_key,
        "reasoning_effort": ctx.reasoning_effort,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "reasoning_tokens": 0,
        "cached_tokens": 0,
        "token_usage": 0,
        "llm_provider": "",
        "llm_model": model,
        "source_layer_counts": {},
        "context_blocks": [],
        "degradation_flags": [],
        "final_response": "",
        "done": False,
        "thread_id": ctx.thread_id,
        "user_id": ctx.user_id,
        "agent_class": getattr(ctx, "agent_class", "advisory"),
        "user_role": getattr(ctx, "user_role", "viewer"),
        "ab_row_id": getattr(ctx, "ab_row_id", None) or "",
        "routing_reason": "not_evaluated",
        "routing_used": False,
        "routing_picked_model": "",
    }

    config = {"configurable": {"thread_id": ctx.thread_id}}

    from agent.tracing import session_span, set_session_summary

    # exec-18: Create session row at start
    db_session = None
    try:
        from agent.sessions import create_session

        db_session = create_session(
            session_type="agent_chat",
            agent_id=getattr(ctx, "agent_id", "default"),
            user_id=ctx.user_id,
            thread_id=ctx.thread_id,
            bank_id=_memory_bank_id_for_user(ctx.user_id),
        )
    except Exception:  # noqa: BLE001
        pass

    with session_span(
        db_session.session_id if db_session else ctx.thread_id,
        ctx.user_id, "agent_chat", "default"
    ) as _session_span:
        try:
            text_id = "t1"
            yield sse(TextStartPacket(id=text_id))

            result = await graph.ainvoke(initial_state, config=config)

            final = result.get("final_response", "")
            if final:
                # P3: Scan agent output for exfiltration anomalies
                from agent.middleware.sanitizer import scan_output_anomalies

                anomaly = scan_output_anomalies(final)
                if not anomaly.clean:
                    import logging as _log

                    _log.getLogger(__name__).warning(
                        "Output anomalies in agent response: %s",
                        anomaly.anomalies,
                    )
                yield sse(TextDeltaPacket(id=text_id, delta=final))

            tool_results = result.get("tool_results", [])
            if tool_results:
                # Step boundary: tool execution happened before final response
                yield sse(StepStartPacket())
                for tr in tool_results:
                    yield sse(
                        ToolStartPacket(
                            tool_name=tr["tool_name"], tool_call_id=tr["tool_call_id"]
                        )
                    )
                    if tr.get("error"):
                        yield sse(
                            ToolErrorPacket(
                                tool_call_id=tr["tool_call_id"], error_text=tr["error"]
                            )
                        )
                    else:
                        yield sse(
                            ToolResultPacket(
                                tool_call_id=tr["tool_call_id"], output=tr["result"]
                            )
                        )

            yield sse(TextEndPacket(id=text_id))
            # ADR-001 G5: forward routing-decision info to frontend so the
            # agent-chat UI can show a user-visible indicator when a cheap
            # model was silently picked. The values originate in router_node
            # (which sets the state keys) and flow through the full graph
            # invocation.
            routing_used = bool(result.get("routing_used"))
            routing_reason = str(result.get("routing_reason") or "not_evaluated")
            routing_picked = str(result.get("routing_picked_model") or "")

            message_metadata = {
                "threadId": ctx.thread_id,
                "promptTokens": int(result.get("prompt_tokens", 0) or 0),
                "completionTokens": int(result.get("completion_tokens", 0) or 0),
                "reasoningTokens": int(result.get("reasoning_tokens", 0) or 0),
                "cachedTokens": int(result.get("cached_tokens", 0) or 0),
                "totalTokens": int(result.get("token_usage", 0) or 0),
                "provider": str(result.get("llm_provider", "") or "litellm"),
                "model": str(result.get("llm_model", "") or model),
                "sourceLayerCounts": result.get("source_layer_counts", {}) or {},
                "degradationFlags": result.get("degradation_flags", []) or [],
                "contextBlocks": result.get("context_blocks", []) or [],
                "queryGate": result.get("query_gate") or {},
                "routingUsed": routing_used,
                "routingReason": routing_reason,
                "routingPicked": routing_picked,
            }
            yield sse(
                MessageMetaPacket(
                    message_metadata=message_metadata
                )
            )
            set_session_summary(
                _session_span,
                total_turns=result.get("iteration", 0),
                total_tokens=result.get("token_usage", 0),
                outcome="completed",
            )

            # exec-18: Update session with completion
            if db_session:
                try:
                    from agent.sessions import update_session

                    session_summary = {
                        "total_turns": int(result.get("iteration", 0) or 0),
                        "total_tokens": int(result.get("token_usage", 0) or 0),
                        "totalTokens": int(result.get("token_usage", 0) or 0),
                        "promptTokens": int(result.get("prompt_tokens", 0) or 0),
                        "completionTokens": int(result.get("completion_tokens", 0) or 0),
                        "reasoningTokens": int(result.get("reasoning_tokens", 0) or 0),
                        "cachedTokens": int(result.get("cached_tokens", 0) or 0),
                        "provider": str(result.get("llm_provider", "") or "litellm"),
                        "model": str(result.get("llm_model", "") or model),
                        "sourceLayerCounts": result.get("source_layer_counts", {}) or {},
                        "degradationFlags": result.get("degradation_flags", []) or [],
                        "queryGate": result.get("query_gate") or {},
                    }
                    update_session(
                        db_session.session_id,
                        status="completed",
                        summary=session_summary,
                        metadata={"latest_run": message_metadata},
                    )
                except Exception:  # noqa: BLE001
                    pass

            # exec-hermes Phase-B P1: fire-and-forget memory sync. ADR:
            # turn-latency wins over strong-persistence in Phase-B; errors
            # surface via agent.sync_failures table + span-event.
            # Phase-C migrates to at-least-once delivery via NATS if
            # measured data-loss impact justifies the complexity.
            try:
                asyncio.create_task(
                    _safe_sync_turn(
                        user_id=ctx.user_id,
                        thread_id=ctx.thread_id,
                        messages=messages,
                        final_response=final,
                    )
                )
            except Exception:  # noqa: BLE001 — task-create must never block response
                logger.debug("sync_turn task dispatch failed", exc_info=True)

            # exec-06 §4d Phase 5: fire-and-forget session title-gen after
            # the first assistant reply. persist_session_title is
            # idempotent (only sets title when the column is NULL/empty)
            # so calling on every turn is safe; the UPDATE becomes a
            # no-op once a title has been generated. Service-credential
            # lives in MATRIX_TITLE_GEN_KEY (absent → skipped silently,
            # no user-quota consumption, no billing span).
            if db_session and final:
                try:
                    from agent.titles.generator import generate_and_persist_title

                    last_user = _last_user_text(messages) or ""
                    asyncio.create_task(
                        generate_and_persist_title(
                            session_id=db_session.session_id,
                            user_message=last_user[:500],
                            assistant_reply=final[:500],
                        )
                    )
                except Exception:  # noqa: BLE001 — title-gen must never break the turn
                    logger.debug("title-gen task dispatch failed", exc_info=True)

            yield sse(FinishPacket(finish_reason="stop"))

        except Exception as e:
            set_session_summary(_session_span, outcome="error")
            if db_session:
                try:
                    from agent.sessions import update_session

                    update_session(db_session.session_id, status="errored")
                except Exception:  # noqa: BLE001
                    pass
            # exec-hermes §3.4: classify for telemetry in ErrorPacket.metadata
            # (failover orchestration itself belongs to exec-16 Provider-Fallback-Chain).
            from agent.streaming import build_error_packet_with_failover

            yield sse(build_error_packet_with_failover(e, prefix="LangGraph error: "))


async def _safe_sync_turn(
    *,
    user_id: str,
    thread_id: str,
    messages: list[dict],
    final_response: str,
) -> None:
    """Fire-and-forget memory-sync wrapper.

    exec-hermes Phase-B P1: runs as ``asyncio.create_task`` after the
    LangGraph turn finishes. The happy-path writes user-message +
    assistant-response to every :class:`MemoryProvider` in the
    :class:`MemoryManager` fan-out. Failures are caught + logged +
    optionally recorded in ``agent.sync_failures`` for ops-visibility
    (the table is probed at startup; when missing the INSERT branch is
    skipped so rolling-deploy pod-starts-before-migration don't produce
    a second failure).

    ADR: see migration ``022_agent_sync_failures`` header-doc for the
    Phase-B debt and Phase-C NATS-JetStream migration path.
    """
    from memory_fusion.memory_provider import get_memory_manager

    manager = get_memory_manager()
    if manager is None:
        return

    # Extract last user + assistant exchange
    last_user = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                last_user = content
                break

    try:
        from memory_fusion.engine import get_bank_id

        await manager.sync_turn(
            user_message=last_user,
            assistant_message=final_response,
            user_id=user_id,
            bank_id=get_bank_id(user_id) if user_id else "",
        )
    except Exception as exc:  # noqa: BLE001 — fire-and-forget contract
        logger.warning(
            "memory sync_turn failed user_id=%s thread_id=%s: %s",
            user_id, thread_id, exc,
        )
        await _record_sync_failure(
            user_id=user_id, thread_id=thread_id, error=str(exc),
        )


async def _record_sync_failure(
    *, user_id: str, thread_id: str, error: str
) -> None:
    """Best-effort INSERT into ``agent.sync_failures`` for ops-visibility.

    Only runs when the table was probed successfully at startup (see
    ``agent.resilience.init_stack._probe_sync_failures_table``) — avoids
    silent double-failure during rolling deploys where the pod starts
    before the migration runs.
    """
    try:
        from agent.resilience.init_stack import init_status

        status = init_status()
        if not status.sync_failures_table.up:
            return
    except Exception:
        return

    try:
        import os

        import asyncpg

        dsn = (
            os.environ.get("SCHEDULER_DB_URL")
            or os.environ.get("HINDSIGHT_DB_URL")
            or os.environ.get("AUDIT_DB_URL")
        )
        if not dsn:
            return
        conn = await asyncpg.connect(dsn=dsn, timeout=2.0)
        try:
            await conn.execute(
                "INSERT INTO agent.sync_failures "
                "(user_id, thread_id, error) VALUES ($1, $2, $3)",
                user_id, thread_id, error[:2000],
            )
        finally:
            await conn.close()
    except Exception:  # noqa: BLE001 — visibility-log must not raise
        logger.debug("sync_failures INSERT skipped", exc_info=True)
