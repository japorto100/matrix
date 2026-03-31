# run_agent_loop — Phase 22g / ABP.1
# LLM-agnostic agent loop: Anthropic SDK + OpenAI-compatible + LiteLLM multi-provider router.
# Patterns from AgentZero (extension hooks, error hierarchy) + Onyx (parallel tools, immutable ctx).
#
# Provider routing:
#   AGENT_PROVIDER=anthropic         → Anthropic SDK (default, tool-call loop)
#   AGENT_PROVIDER=openai            → OpenAI API (tool-call loop via function calling)
#   AGENT_PROVIDER=openai-compatible → any OpenAI-compatible: OpenRouter, Ollama, vLLM, Azure
#     OPENAI_BASE_URL=<url>          → target URL (e.g. http://localhost:11434/v1 for Ollama)
#     OPENAI_API_KEY=<key>           → api key (or "ollama" / "not-set" for local)
#   AGENT_USE_LITELLM=true           → LiteLLM router (multi-provider, keys from env)
#     AGENT_MODEL=anthropic/claude-opus-4-6  → model string (provider prefix optional)
#     AGENT_PROVIDER_FALLBACKS=anthropic,openai,ollama → comma-sep fallback chain
#
# Architecture: Frontend → Go Gateway (control/routing) → here (LLM calls).
# LiteLLM reads API keys directly from env (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.) — no proxy needed.
# Go remains the auth boundary + SSE relay.

from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncGenerator

import anyio

from agent.context import AgentExecutionContext
from agent.errors import (
    CriticalError,
    RepairableError,
    ToolValidationError,
)
from agent.extensions import get_extension_registry
from agent.streaming import (
    ApprovalRequestPacket,
    ErrorPacket,
    FinishPacket,
    MessageMetaPacket,
    TextDeltaPacket,
    TextEndPacket,
    TextStartPacket,
    ThreadIdPacket,
    ToolErrorPacket,
    ToolResultPacket,
    ToolStartPacket,
    sse,
)
from agent.validators.trading import needs_approval, validate_tool_call

MAX_ITERATIONS = 10
TEXT_BLOCK_ID = "t1"
# ABP.2d: per-tool execution timeout — prevents a single hanging call from blocking the loop.
TOOL_TIMEOUT_SEC = float(os.environ.get("AGENT_TOOL_TIMEOUT_SEC", "30"))

# AC.LLM-A4: Ordered fallback chain for LiteLLM router.
# Each entry is a litellm provider prefix (e.g. "anthropic", "openai", "ollama").
PROVIDER_FALLBACKS: list[str] = [
    p.strip()
    for p in os.environ.get("AGENT_PROVIDER_FALLBACKS", "anthropic,openai,ollama").split(",")
    if p.strip()
]

_REASONING_BUDGET: dict[str, int] = {
    "low": 1024,
    "medium": 4096,
    "high": 16384,
}


async def run_agent_loop(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """
    LLM-agnostic agent loop — routes to LangGraph or legacy backend.
    Yields SSE strings (Vercel AI Data Stream Protocol).

    exec-10: LangGraph as primary (AGENT_USE_LANGGRAPH=true, default).
    Legacy: manual while-loop (AGENT_USE_LANGGRAPH=false).
    """
    use_langgraph = os.environ.get("AGENT_USE_LANGGRAPH", "true").lower() == "true"

    # ACR-G7: thread-id as first event
    yield sse(ThreadIdPacket(threadId=ctx.thread_id))

    # exec-10: Skill Injection — Skills ins System-Prompt laden
    system_prompt = ctx.system_prompt
    try:
        from agent.skills.loader import load_skills, format_skills_for_prompt
        skills = load_skills(user_id=ctx.user_id)
        skills_text = format_skills_for_prompt(skills)
        if skills_text:
            system_prompt = f"{system_prompt}\n\n{skills_text}"
    except Exception:
        pass  # Skills sind optional

    # exec-10 Phase 3.5: Temporal Context — letzte Interaktionen als Kontext
    try:
        from agent.temporal_context import get_temporal_context
        temporal = get_temporal_context(user_id=ctx.user_id)
        if temporal:
            system_prompt = f"{system_prompt}\n\n{temporal}"
    except Exception:
        pass  # Temporal Context ist optional

    if use_langgraph:
        async for chunk in _loop_langgraph(ctx, messages, system_prompt):
            yield chunk
    else:
        async for chunk in _loop_legacy(ctx, messages):
            yield chunk


async def _loop_langgraph(
    ctx: AgentExecutionContext,
    messages: list[dict],
    system_prompt: str,
) -> AsyncGenerator[str, None]:
    """LangGraph-based agent loop (exec-10).

    Nutzt den Agent Graph (StateGraph) statt manuellem while-Loop.
    Streamt Graph-Events als SSE Packets.
    """
    try:
        from agent.graph.agent_graph import create_agent_graph
        from agent.graph.state import AgentGraphState
    except ImportError as e:
        yield sse(ErrorPacket(error=f"LangGraph import error: {e}"))
        return

    provider = os.environ.get("AGENT_PROVIDER", "anthropic").lower()
    use_litellm = os.environ.get("AGENT_USE_LITELLM", "false").lower() == "true"
    if use_litellm:
        provider = "litellm"

    graph = create_agent_graph()

    initial_state: AgentGraphState = {
        "messages": messages,
        "tool_calls": [],
        "tool_results": [],
        "iteration": 0,
        "max_iterations": MAX_ITERATIONS,
        "current_role": "default",
        "system_prompt": system_prompt,
        "model": ctx.model,
        "provider": provider,
        "reasoning_effort": ctx.reasoning_effort,
        "final_response": "",
        "done": False,
        "thread_id": ctx.thread_id,
        "user_id": ctx.user_id,
    }

    config = {"configurable": {"thread_id": ctx.thread_id}}

    try:
        # Graph ausfuehren und Events streamen
        text_id = "t1"
        yield sse(TextStartPacket(id=text_id))

        result = await graph.ainvoke(initial_state, config=config)

        final = result.get("final_response", "")
        if final:
            yield sse(TextDeltaPacket(id=text_id, text=final))

        # Tool Results als SSE Events
        for tr in result.get("tool_results", []):
            yield sse(ToolStartPacket(tool_name=tr["tool_name"], tool_call_id=tr["tool_call_id"]))
            if tr.get("error"):
                yield sse(ToolErrorPacket(tool_call_id=tr["tool_call_id"], error=tr["error"]))
            else:
                yield sse(ToolResultPacket(tool_call_id=tr["tool_call_id"], result=tr["result"]))

        yield sse(TextEndPacket(id=text_id))

        # Usage metadata
        yield sse(MessageMetaPacket(metadata={
            "threadId": ctx.thread_id,
            "promptTokens": 0,  # TODO: extract from graph result
            "completionTokens": 0,
        }))
        yield sse(FinishPacket(finishReason="stop"))

    except Exception as e:
        yield sse(ErrorPacket(error=f"LangGraph error: {e}"))


async def _loop_legacy(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Legacy agent loop — manual while-loop (pre-exec-10 fallback)."""
    provider = os.environ.get("AGENT_PROVIDER", "anthropic").lower()
    use_litellm = os.environ.get("AGENT_USE_LITELLM", "false").lower() == "true"

    if use_litellm:
        async for chunk in _loop_litellm(ctx, messages):
            yield chunk
    elif provider in ("openai", "openai-compatible"):
        async for chunk in _loop_openai(ctx, messages):
            yield chunk
    else:
        async for chunk in _loop_anthropic(ctx, messages):
            yield chunk


# ── Anthropic loop ────────────────────────────────────────────────────────────

async def _loop_anthropic(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Tool-capable agent loop using Anthropic SDK. Supports extended thinking (AC108)."""
    try:
        from anthropic import AsyncAnthropic, APIError, APIStatusError
        from anthropic.types import RawContentBlockDeltaEvent, TextDelta
    except ImportError:
        yield sse(ErrorPacket(error="anthropic package not installed"))
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        yield sse(ErrorPacket(error="ANTHROPIC_API_KEY not configured"))
        return

    client = AsyncAnthropic(api_key=api_key)
    ext = get_extension_registry()
    tool_defs = ctx.tool_definitions()
    prompt_tokens = 0
    completion_tokens = 0

    for iteration in range(MAX_ITERATIONS):
        stream_kwargs: dict = {
            "model": ctx.model,
            "system": ctx.system_prompt,
            "messages": messages,
            "max_tokens": _max_tokens_anthropic(ctx),
        }
        if tool_defs:
            stream_kwargs["tools"] = tool_defs
        _apply_reasoning(ctx, stream_kwargs)

        if iteration == 0:
            yield sse(TextStartPacket(id=TEXT_BLOCK_ID))

        try:
            async with client.messages.stream(**stream_kwargs) as stream:
                async for event in stream:
                    if isinstance(event, RawContentBlockDeltaEvent) and isinstance(event.delta, TextDelta):
                        delta = event.delta.text
                        if delta:
                            yield sse(TextDeltaPacket(delta=delta, id=TEXT_BLOCK_ID))
                            await ext.fire_stream_chunk(ctx.thread_id, delta)
                final = await stream.get_final_message()
                prompt_tokens += final.usage.input_tokens
                completion_tokens += final.usage.output_tokens
        except APIStatusError as e:
            yield sse(ErrorPacket(error=f"Anthropic API error {e.status_code}: {e.message}"))
            return
        except APIError as e:
            yield sse(ErrorPacket(error=f"Anthropic API error: {e.message}"))
            return
        except Exception as e:
            yield sse(ErrorPacket(error=str(e)))
            return

        await ext.fire_response_end(ctx.thread_id, final)

        if final.stop_reason == "end_turn":
            break

        tool_uses = [b for b in final.content if b.type == "tool_use"]
        if not tool_uses:
            break

        tool_results = await _execute_tools_parallel_anthropic(tool_uses, ctx)
        for event_sse in tool_results["events"]:
            yield event_sse

        messages = list(messages)
        messages.append({"role": "assistant", "content": final.content})
        messages.append({"role": "user", "content": tool_results["result_blocks"]})

    else:
        yield sse(ErrorPacket(error=f"Agent loop exceeded {MAX_ITERATIONS} iterations"))
        return

    yield sse(TextEndPacket(id=TEXT_BLOCK_ID))
    yield sse(MessageMetaPacket(metadata={
        "promptTokens": prompt_tokens,
        "completionTokens": completion_tokens,
        "threadId": ctx.thread_id,
    }))
    yield sse(FinishPacket(finishReason="stop"))


# ── OpenAI-compatible loop ────────────────────────────────────────────────────

async def _loop_openai(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Tool-capable agent loop using OpenAI SDK.
    Covers: OpenAI API, OpenRouter (OPENAI_BASE_URL=https://openrouter.ai/api/v1),
            Ollama (OPENAI_BASE_URL=http://localhost:11434/v1, OPENAI_API_KEY=ollama),
            vLLM, Azure OpenAI, LM Studio, any OpenAI-compatible endpoint.
    """
    try:
        from openai import AsyncOpenAI, APIError, APIStatusError
    except ImportError:
        yield sse(ErrorPacket(error="openai package not installed"))
        return

    api_key = os.environ.get("OPENAI_API_KEY", "not-set")
    base_url = os.environ.get("OPENAI_BASE_URL")  # None = default OpenAI
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    ext = get_extension_registry()
    # Convert Anthropic tool defs → OpenAI function format
    openai_tools = _anthropic_tools_to_openai(ctx.tool_definitions())
    prompt_tokens = 0
    completion_tokens = 0

    # Prepend system message to OpenAI messages
    oa_messages: list[dict] = [{"role": "system", "content": ctx.system_prompt}] + list(messages)

    for iteration in range(MAX_ITERATIONS):
        if iteration == 0:
            yield sse(TextStartPacket(id=TEXT_BLOCK_ID))

        try:
            kwargs: dict = {
                "model": ctx.model,
                "messages": oa_messages,
                "max_tokens": 4096,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"

            accumulated_text = ""
            tool_calls_acc: dict[int, dict] = {}  # index → {id, name, arguments_str}
            finish_reason = "stop"
            chunk = None

            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.usage:
                    prompt_tokens += chunk.usage.prompt_tokens or 0
                    completion_tokens += chunk.usage.completion_tokens or 0
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                # Text delta
                if delta.content:
                    yield sse(TextDeltaPacket(delta=delta.content, id=TEXT_BLOCK_ID))
                    accumulated_text += delta.content
                    await ext.fire_stream_chunk(ctx.thread_id, delta.content)
                # Tool call streaming
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            tool_calls_acc[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls_acc[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc.function.arguments
            if chunk is not None and chunk.choices:
                finish_reason = chunk.choices[0].finish_reason or "stop"

        except APIStatusError as e:
            yield sse(ErrorPacket(error=f"OpenAI API error {e.status_code}: {e.message}"))
            return
        except APIError as e:
            yield sse(ErrorPacket(error=f"OpenAI API error: {e.message}"))
            return
        except Exception as e:
            yield sse(ErrorPacket(error=str(e)))
            return

        if finish_reason != "tool_calls" or not tool_calls_acc:
            break

        # Execute tool calls (parallel)
        tool_call_list = list(tool_calls_acc.values())
        tool_results = await _execute_tools_parallel_openai(tool_call_list, ctx)
        for event_sse in tool_results["events"]:
            yield event_sse

        # Append assistant message with tool_calls + tool results
        oa_messages = list(oa_messages)
        oa_messages.append({
            "role": "assistant",
            "content": accumulated_text or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_call_list
            ],
        })
        for result_msg in tool_results["result_messages"]:
            oa_messages.append(result_msg)

    else:
        yield sse(ErrorPacket(error=f"Agent loop exceeded {MAX_ITERATIONS} iterations"))
        return

    yield sse(TextEndPacket(id=TEXT_BLOCK_ID))
    yield sse(MessageMetaPacket(metadata={
        "promptTokens": prompt_tokens,
        "completionTokens": completion_tokens,
        "threadId": ctx.thread_id,
    }))
    yield sse(FinishPacket(finishReason="stop"))


# ── LiteLLM multi-provider loop ───────────────────────────────────────────────

async def _loop_litellm(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """
    AC.LLM-A2: Multi-provider agent loop via LiteLLM router.
    Reads API keys from env (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.) — no proxy.
    Model string format: "anthropic/claude-opus-4-6", "gpt-4o", "ollama/llama3", etc.
    Fallback chain: AGENT_PROVIDER_FALLBACKS env var (default: anthropic,openai,ollama).
    """
    try:
        import litellm
    except ImportError:
        yield sse(ErrorPacket(error="litellm package not installed"))
        return

    model = ctx.model or os.environ.get("AGENT_MODEL", "anthropic/claude-opus-4-6")
    ext = get_extension_registry()
    # LiteLLM uses OpenAI-compatible tool format
    openai_tools = _anthropic_tools_to_openai(ctx.tool_definitions())
    prompt_tokens = 0
    completion_tokens = 0

    # System message prepended (LiteLLM OpenAI-compat format)
    ll_messages: list[dict] = [{"role": "system", "content": ctx.system_prompt}] + list(messages)

    # Build fallback list: [{"model": "openai/gpt-4o"}, {"model": "ollama/llama3"}]
    # First entry is the primary model; remaining from PROVIDER_FALLBACKS (skip primary's provider).
    primary_provider = model.split("/")[0] if "/" in model else None
    fallbacks = [
        {"model": f"{p}/{model.split('/')[-1]}" if primary_provider else model}
        for p in PROVIDER_FALLBACKS
        if p != primary_provider
    ]

    for iteration in range(MAX_ITERATIONS):
        if iteration == 0:
            yield sse(TextStartPacket(id=TEXT_BLOCK_ID))

        try:
            kwargs: dict = {
                "model": model,
                "messages": ll_messages,
                "max_tokens": 4096,
                "stream": True,
            }
            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"
            if fallbacks:
                kwargs["fallbacks"] = fallbacks

            accumulated_text = ""
            tool_calls_acc: dict[int, dict] = {}
            finish_reason = "stop"
            chunk = None

            response = await litellm.acompletion(**kwargs)
            async for chunk in response:
                if hasattr(chunk, "usage") and chunk.usage:
                    prompt_tokens += getattr(chunk.usage, "prompt_tokens", 0) or 0
                    completion_tokens += getattr(chunk.usage, "completion_tokens", 0) or 0
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    yield sse(TextDeltaPacket(delta=delta.content, id=TEXT_BLOCK_ID))
                    accumulated_text += delta.content
                    await ext.fire_stream_chunk(ctx.thread_id, delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            tool_calls_acc[idx]["id"] = tc.id
                        if tc.function and tc.function.name:
                            tool_calls_acc[idx]["name"] = tc.function.name
                        if tc.function and tc.function.arguments:
                            tool_calls_acc[idx]["arguments"] += tc.function.arguments
            if chunk is not None and chunk.choices:
                finish_reason = chunk.choices[0].finish_reason or "stop"

        except Exception as e:
            yield sse(ErrorPacket(error=f"LiteLLM error: {e}"))
            return

        if finish_reason != "tool_calls" or not tool_calls_acc:
            break

        tool_call_list = list(tool_calls_acc.values())
        tool_results = await _execute_tools_parallel_openai(tool_call_list, ctx)
        for event_sse in tool_results["events"]:
            yield event_sse

        ll_messages = list(ll_messages)
        ll_messages.append({
            "role": "assistant",
            "content": accumulated_text or None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_call_list
            ],
        })
        for result_msg in tool_results["result_messages"]:
            ll_messages.append(result_msg)

    else:
        yield sse(ErrorPacket(error=f"Agent loop exceeded {MAX_ITERATIONS} iterations"))
        return

    yield sse(TextEndPacket(id=TEXT_BLOCK_ID))
    yield sse(MessageMetaPacket(metadata={
        "promptTokens": prompt_tokens,
        "completionTokens": completion_tokens,
        "threadId": ctx.thread_id,
    }))
    yield sse(FinishPacket(finishReason="stop"))


# ── Tool execution helpers ─────────────────────────────────────────────────────

async def _execute_tools_parallel_anthropic(
    tool_uses: list,
    ctx: AgentExecutionContext,
) -> dict:
    """Parallel Anthropic tool execution. Returns events + result_blocks."""

    async def _run_one(tool_use) -> tuple[list[str], dict]:
        return await _run_tool(
            tool_name=tool_use.name,
            tool_call_id=tool_use.id,
            tool_input=dict(tool_use.input) if tool_use.input else {},
            ctx=ctx,
            result_format="anthropic",
        )

    return await _gather_tool_results(tool_uses, _run_one, result_key="result_blocks")


async def _execute_tools_parallel_openai(
    tool_calls: list[dict],
    ctx: AgentExecutionContext,
) -> dict:
    """Parallel OpenAI tool execution. Returns events + result_messages."""

    async def _run_one(tc: dict) -> tuple[list[str], dict]:
        try:
            tool_input = json.loads(tc["arguments"]) if tc["arguments"] else {}
        except json.JSONDecodeError:
            tool_input = {}
        return await _run_tool(
            tool_name=tc["name"],
            tool_call_id=tc["id"],
            tool_input=tool_input,
            ctx=ctx,
            result_format="openai",
        )

    return await _gather_tool_results(tool_calls, _run_one, result_key="result_messages")


async def _run_tool(
    tool_name: str,
    tool_call_id: str,
    tool_input: dict,
    ctx: AgentExecutionContext,
    result_format: str,  # "anthropic" | "openai"
) -> tuple[list[str], dict]:
    local_events: list[str] = []
    ext = get_extension_registry()

    local_events.append(sse(ToolStartPacket(tool_name=tool_name, tool_call_id=tool_call_id)))
    await ext.fire_tool_before(ctx.thread_id, tool_name, tool_input)

    def _error_block(msg: str) -> dict:
        if result_format == "openai":
            return {"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps({"error": msg, "ok": False})}
        return {"type": "tool_result", "tool_use_id": tool_call_id, "content": json.dumps({"error": msg, "ok": False}), "is_error": True}

    try:
        validate_tool_call(tool_name, tool_input, ctx)
    except ToolValidationError as e:
        local_events.append(sse(ToolErrorPacket(tool_call_id=tool_call_id, error=str(e))))
        return local_events, _error_block(str(e))
    except CriticalError:
        raise

    if needs_approval(tool_name, ctx):
        local_events.append(sse(ApprovalRequestPacket(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            tool_input=tool_input,
        )))
        pending = {"status": "pending_approval", "ok": False}
        if result_format == "openai":
            return local_events, {"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps(pending)}
        return local_events, {"type": "tool_result", "tool_use_id": tool_call_id, "content": json.dumps(pending)}

    tool = ctx.find_tool(tool_name)
    if tool is None:
        err = f"Tool '{tool_name}' not found in registry"
        local_events.append(sse(ToolErrorPacket(tool_call_id=tool_call_id, error=err)))
        return local_events, _error_block(err)

    try:
        tool.validate(tool_input, ctx)
        # ABP.2d: anyio cancel scope — prevents a hanging tool from blocking the loop.
        with anyio.move_on_after(TOOL_TIMEOUT_SEC) as cancel_scope:
            result = await tool.execute(tool_input, ctx)
        if cancel_scope.cancelled_caught:
            result = {
                "error": f"tool '{tool_name}' timed out after {TOOL_TIMEOUT_SEC}s",
                "timed_out": True,
            }
    except RepairableError as e:
        local_events.append(sse(ToolErrorPacket(tool_call_id=tool_call_id, error=str(e))))
        return local_events, _error_block(str(e))
    except Exception as e:
        err = f"Tool execution error: {e}"
        local_events.append(sse(ToolErrorPacket(tool_call_id=tool_call_id, error=err)))
        return local_events, _error_block(err)

    await ext.fire_tool_after(ctx.thread_id, tool_name, tool_input, result)
    # UI bekommt das volle Ergebnis
    local_events.append(sse(ToolResultPacket(tool_call_id=tool_call_id, result=result)))

    # LLM bekommt ggf. gekürztes Ergebnis (toModelOutput) — spart Tokens bei großen Outputs
    model_output = tool.to_model_output(result)
    model_content = json.dumps(model_output) if isinstance(model_output, dict) else str(model_output)

    if result_format == "openai":
        result_block = {"role": "tool", "tool_call_id": tool_call_id, "content": model_content}
    else:
        result_block = {"type": "tool_result", "tool_use_id": tool_call_id, "content": model_content}

    return local_events, result_block


async def _gather_tool_results(items: list, run_fn, result_key: str) -> dict:
    tasks = [run_fn(item) for item in items]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    events: list[str] = []
    results: list[dict] = []
    for item in gathered:
        if isinstance(item, CriticalError):
            raise item
        if isinstance(item, BaseException):
            events.append(sse(ErrorPacket(error=str(item))))
            continue
        local_events, result_block = item
        events.extend(local_events)
        results.append(result_block)

    return {"events": events, result_key: results}


# ── Converters ────────────────────────────────────────────────────────────────

def _anthropic_tools_to_openai(tool_defs: list[dict]) -> list[dict]:
    """Convert Anthropic tool definitions to OpenAI function calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tool_defs
    ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _max_tokens_anthropic(ctx: AgentExecutionContext) -> int:
    if ctx.reasoning_effort and ctx.reasoning_effort in _REASONING_BUDGET:
        return 8192
    return 4096


def _apply_reasoning(ctx: AgentExecutionContext, stream_kwargs: dict) -> None:
    """AC108: extended thinking — Anthropic only."""
    if ctx.reasoning_effort and ctx.reasoning_effort in _REASONING_BUDGET:
        budget = _REASONING_BUDGET[ctx.reasoning_effort]
        stream_kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
