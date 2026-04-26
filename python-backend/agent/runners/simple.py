"""SimpleAgentLoop — pure-asyncio alternative to LangGraph runner (Phase-C P2).

Port of hermes' ``environments/agent_loop.py::HermesAgentLoop`` adapted to
matrix's enterprise contracts. **Additive only** — `agent/graph/runner.py`
(LangGraph) is not touched; this module lives in ``agent/runners/``
deliberately OUTSIDE ``agent/graph/`` since it is NOT graph-based. The
dispatcher (:mod:`agent.runners.dispatcher`) routes per-user A/B traffic
between this and the LangGraph runner.

**Hook-drift resolution (Contrarian-MAJOR-1):**
Instead of re-implementing CredentialPool / MemoryManager / rate-limit /
redact / cost-estimation in this file, we reuse :func:`agent.graph.nodes.llm_node.llm_node`
and :func:`agent.graph.nodes.tool_node.tool_node` as plain async functions.
They already contain every Phase-B hook (acquire/apply_recovery/mark_success,
rate-limit capture, cost span-attrs, classify_error, cache-control, etc.).
Zero duplication → zero drift.

**What this file actually does:**
1. Prep system-prompt + messages via reused :func:`runner._prepare_system_prompt`
   / :func:`runner._prepare_messages`.
2. Run a multi-turn loop: ``llm_node(state)`` → if tool_calls → ``tool_node(state)``
   → repeat until no tool_calls or MAX_ITERATIONS.
3. Emit the identical SSE packet sequence as :func:`runner._run_graph` so
   the frontend cannot tell which runner served the turn.
4. Same session-row bookkeeping, same fire-and-forget ``_safe_sync_turn``.

**Streaming deferred (Contrarian-MAJOR-3 lock):**
LiteLLM supports true token streaming but we deliberately do NOT enable
it here — SimpleLoop must maintain SSE parity with LangGraph's batch
path. Enabling streaming changes the frontend contract (hundreds of
TextDeltaPackets vs. one) and invalidates the A/B comparison. See
exec-hermes §9 "Phase-D streaming" for the planned follow-up.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from agent.context import AgentExecutionContext
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

MAX_ITERATIONS = 25


async def run_simple_agent_loop(
    ctx: AgentExecutionContext,
    messages: list[dict],
    *,
    ab_row_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Dispatcher entry point for the SimpleLoop variant.

    Signature mirrors :func:`agent.graph.runner.run_agent_loop` except
    for the optional ``ab_row_id`` used by
    :mod:`agent.graph.loop_dispatcher` to backfill timing/token/cost data
    into ``agent.ab_experiments`` once the turn is done.
    """
    # Reuse the exact same pre-processing as LangGraph — identical skill
    # injection, temporal context, compaction/compression.
    from agent.graph.runner import (
        _prepare_messages,
        _prepare_system_prompt,
        _safe_sync_turn,
    )

    yield sse(StartPacket(message_id=ctx.thread_id))
    yield sse(MessageMetaPacket(message_metadata={"threadId": ctx.thread_id}))

    system_prompt = await _prepare_system_prompt(ctx, messages)
    messages = await _prepare_messages(messages, ctx)

    async for chunk in _run_simple(ctx, messages, system_prompt, ab_row_id=ab_row_id):
        yield chunk

    # fire-and-forget memory sync (identical to runner.py:447) runs after
    # the final SSE chunk has been yielded.
    try:
        final_response = _last_assistant_text(messages)
        asyncio.create_task(
            _safe_sync_turn(
                user_id=ctx.user_id,
                thread_id=ctx.thread_id,
                messages=messages,
                final_response=final_response,
            )
        )
    except Exception:  # noqa: BLE001
        logger.debug("sync_turn task dispatch failed", exc_info=True)


def _last_assistant_text(msgs: list[dict]) -> str:
    for m in reversed(msgs):
        if isinstance(m, dict) and m.get("role") == "assistant":
            c = m.get("content")
            if isinstance(c, str):
                return c
    return ""


async def _run_simple(
    ctx: AgentExecutionContext,
    messages: list[dict],
    system_prompt: str,
    *,
    ab_row_id: str | None,
) -> AsyncGenerator[str, None]:
    """Core multi-turn loop — delegates to llm_node + tool_node."""
    from agent.graph.nodes.llm_node import llm_node
    from agent.graph.nodes.tool_node import tool_node
    from agent.graph.runner import _memory_bank_id_for_user
    from agent.security.credentials import get_user_role_model
    from agent.sessions import create_session, update_session
    from agent.tracing import session_span, set_session_summary

    model = ctx.model
    try:
        role_model = await get_user_role_model(ctx.user_id, "default")
        if role_model:
            model = role_model
    except Exception:  # noqa: BLE001
        pass

    db_session = None
    try:
        db_session = create_session(
            session_type="agent_chat_simple",  # distinguishes SimpleLoop in ops queries
            agent_id=getattr(ctx, "agent_id", "default"),
            user_id=ctx.user_id,
            thread_id=ctx.thread_id,
            bank_id=_memory_bank_id_for_user(ctx.user_id),
        )
    except Exception:  # noqa: BLE001
        pass

    state: dict[str, Any] = {
        "messages": list(messages),
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
    }

    with session_span(
        db_session.session_id if db_session else ctx.thread_id,
        ctx.user_id, "agent_chat_simple", "default",
    ) as _session_span:
        text_id = "t1"
        all_tool_results: list[dict[str, Any]] = []
        try:
            yield sse(TextStartPacket(id=text_id))

            for iteration in range(MAX_ITERATIONS):
                state["iteration"] = iteration

                # Reuses every Phase-B hook wired into llm_node.
                llm_out = await llm_node(state)
                _merge(state, llm_out)

                tool_calls = state.get("tool_calls") or []
                if not tool_calls:
                    break

                # Reuses tool-dispatch pipeline: timeout enforcement,
                # parallel exec, ToolResult construction.
                tool_out = await tool_node(state)
                new_results = tool_out.get("tool_results") or []
                all_tool_results.extend(new_results)
                _merge(state, tool_out)
                _append_tool_messages(state, tool_calls, new_results)

            final = state.get("final_response", "") or _last_assistant_text(
                state["messages"]
            )
            if final:
                # Reuse anomaly scanner from LangGraph path (runner.py:350-360).
                try:
                    from agent.middleware.sanitizer import scan_output_anomalies

                    anomaly = scan_output_anomalies(final)
                    if not anomaly.clean:
                        logger.warning(
                            "Output anomalies in SimpleLoop response: %s",
                            anomaly.anomalies,
                        )
                except Exception:  # noqa: BLE001
                    pass
                yield sse(TextDeltaPacket(id=text_id, delta=final))

            if all_tool_results:
                yield sse(StepStartPacket())
                for tr in all_tool_results:
                    yield sse(
                        ToolStartPacket(
                            tool_name=tr["tool_name"],
                            tool_call_id=tr["tool_call_id"],
                        )
                    )
                    if tr.get("error"):
                        yield sse(
                            ToolErrorPacket(
                                tool_call_id=tr["tool_call_id"],
                                error_text=tr["error"],
                            )
                        )
                    else:
                        yield sse(
                            ToolResultPacket(
                                tool_call_id=tr["tool_call_id"],
                                output=tr["result"],
                            )
                        )

            yield sse(TextEndPacket(id=text_id))

            message_metadata = {
                "threadId": ctx.thread_id,
                "promptTokens": int(state.get("prompt_tokens", 0) or 0),
                "completionTokens": int(state.get("completion_tokens", 0) or 0),
                "reasoningTokens": int(state.get("reasoning_tokens", 0) or 0),
                "cachedTokens": int(state.get("cached_tokens", 0) or 0),
                "totalTokens": int(state.get("token_usage", 0) or 0),
                "provider": str(state.get("llm_provider", "") or "litellm"),
                "model": str(state.get("llm_model", "") or model),
                "sourceLayerCounts": state.get("source_layer_counts", {}) or {},
                "degradationFlags": state.get("degradation_flags", []) or [],
                "contextBlocks": state.get("context_blocks", []) or [],
                "queryGate": state.get("query_gate") or {},
                "runner": "simple",
            }
            yield sse(MessageMetaPacket(message_metadata=message_metadata))

            set_session_summary(
                _session_span,
                total_turns=state.get("iteration", 0),
                total_tokens=state.get("token_usage", 0),
                outcome="completed",
            )

            if db_session:
                try:
                    update_session(
                        db_session.session_id,
                        status="completed",
                        summary={
                            "total_turns": int(state.get("iteration", 0) or 0),
                            "total_tokens": int(state.get("token_usage", 0) or 0),
                            "promptTokens": int(state.get("prompt_tokens", 0) or 0),
                            "completionTokens": int(state.get("completion_tokens", 0) or 0),
                            "reasoningTokens": int(state.get("reasoning_tokens", 0) or 0),
                            "cachedTokens": int(state.get("cached_tokens", 0) or 0),
                            "provider": message_metadata["provider"],
                            "model": message_metadata["model"],
                            "runner": "simple",
                        },
                        metadata={"latest_run": message_metadata},
                    )
                except Exception:  # noqa: BLE001
                    pass

            # Backfill A/B row with final metrics — fire-and-forget.
            if ab_row_id:
                asyncio.create_task(
                    _finalize_ab_row(
                        ab_row_id,
                        prompt_tokens=int(state.get("prompt_tokens", 0) or 0),
                        completion_tokens=int(state.get("completion_tokens", 0) or 0),
                        turns_used=int(state.get("iteration", 0) or 0),
                        finished_naturally=True,
                        session_id=(
                            db_session.session_id if db_session else None
                        ),
                    )
                )

            yield sse(FinishPacket(finish_reason="stop"))

        except Exception as exc:
            set_session_summary(_session_span, outcome="error")
            if db_session:
                try:
                    update_session(db_session.session_id, status="errored")
                except Exception:  # noqa: BLE001
                    pass

            # The dispatcher (loop_dispatcher.py) catches SimpleLoop
            # exceptions and does NOT fall back silently — it emits a
            # TextEndPacket + ErrorPacket with runner="simple" so the
            # frontend sees a clean error boundary. Re-raise here so the
            # dispatcher's except-clause fires.
            if ab_row_id:
                asyncio.create_task(
                    _finalize_ab_row(
                        ab_row_id,
                        finished_naturally=False,
                        error=f"{type(exc).__name__}: {exc}"[:500],
                        turns_used=int(state.get("iteration", 0) or 0),
                    )
                )
            raise


def _merge(state: dict[str, Any], delta: dict[str, Any]) -> None:
    """Merge a node-return dict into state, same semantics as LangGraph add-reducer."""
    for k, v in delta.items():
        if k == "messages" and isinstance(v, list):
            state["messages"].extend(v)
        else:
            state[k] = v


def _append_tool_messages(
    state: dict[str, Any],
    tool_calls: list[Any],
    tool_results: list[dict[str, Any]],
) -> None:
    """Append tool-role messages so the next llm_node call sees the results.

    OpenAI tool-calling loop requires a ``tool`` role message per tool_call_id
    with its stringified result. LangGraph's ``increment`` node does this
    implicitly via state reducers; SimpleLoop does it explicitly.
    """
    import json as _json

    # First add the assistant message with tool_calls (if not already present).
    last = state["messages"][-1] if state["messages"] else None
    if not last or last.get("role") != "assistant" or not last.get("tool_calls"):
        state["messages"].append(
            {
                "role": "assistant",
                "content": state.get("final_response", "") or "",
                "tool_calls": [
                    {
                        "id": _tool_call_value(tc, "tool_call_id", "id"),
                        "type": "function",
                        "function": {
                            "name": _tool_call_value(tc, "tool_name", "name"),
                            "arguments": _tool_call_arguments(tc),
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

    for tr in tool_results:
        content = tr.get("error") or tr.get("result") or ""
        if not isinstance(content, str):
            content = _json.dumps(content, default=str)
        state["messages"].append(
            {
                "role": "tool",
                "tool_call_id": tr["tool_call_id"],
                "content": content,
            }
        )


def _tool_call_value(tool_call: Any, primary: str, fallback: str) -> Any:
    """Read tool-call fields from either ToolCall objects or dict payloads."""
    if isinstance(tool_call, dict):
        if primary in tool_call:
            return tool_call[primary]
        if fallback in tool_call:
            return tool_call[fallback]
        function = tool_call.get("function")
        if isinstance(function, dict):
            return function.get(fallback) or function.get(primary)
        return None
    return getattr(tool_call, primary, getattr(tool_call, fallback, None))


def _tool_call_arguments(tool_call: Any) -> str:
    import json as _json

    value = _tool_call_value(tool_call, "tool_input", "arguments")
    if isinstance(value, str):
        return value
    return _json.dumps(value or {}, default=str)


async def _finalize_ab_row(
    row_id: str,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    turns_used: int | None = None,
    finished_naturally: bool | None = None,
    error: str | None = None,
    session_id: str | None = None,
) -> None:
    """Fire-and-forget UPDATE on agent.ab_experiments after turn finishes.

    Called via ``asyncio.create_task`` so it never blocks the SSE stream.
    Silent on DB error — the row stays in its initial state with finish
    fields NULL, which the aggregation query already tolerates.
    """
    try:
        import os

        import psycopg

        dsn = os.environ.get(
            "HINDSIGHT_DB_URL",
            "postgresql://postgres@localhost:5433/hindsight_dev",
        )
        async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
            await conn.execute(
                """
                UPDATE agent.ab_experiments
                SET finished_at   = now(),
                    duration_ms   = EXTRACT(EPOCH FROM (now() - started_at)) * 1000,
                    prompt_tokens     = COALESCE(%s, prompt_tokens),
                    completion_tokens = COALESCE(%s, completion_tokens),
                    turns_used        = COALESCE(%s, turns_used),
                    finished_naturally = COALESCE(%s, finished_naturally),
                    error             = COALESCE(%s, error),
                    session_id        = COALESCE(%s, session_id)
                WHERE id = %s
                """,
                (
                    prompt_tokens,
                    completion_tokens,
                    turns_used,
                    finished_naturally,
                    error,
                    session_id,
                    row_id,
                ),
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("ab_experiments UPDATE failed: %s", exc)
