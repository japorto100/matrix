# Agent Graph Runner — exec-12 refactor (was agent/loop.py)
# Entry point: run_agent_loop() → pre-processing → LangGraph execution → SSE stream.
# Legacy manual while-loop removed — LangGraph is the only execution path.

from __future__ import annotations

import os
from typing import AsyncGenerator

from agent.context import AgentExecutionContext
from agent.graph.agent_graph import create_agent_graph, MAX_ITERATIONS
from agent.streaming import (
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


async def run_agent_loop(
    ctx: AgentExecutionContext,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Agent entry point — pre-processing → LangGraph → SSE stream.

    Yields SSE strings (Vercel AI Data Stream Protocol).
    Called from agent/app.py via _stream_agent_loop().
    """
    # ACR-G7: thread-id as first event
    yield sse(ThreadIdPacket(threadId=ctx.thread_id))

    # Pre-processing: Skills, Temporal Context, Summarization, Dangling Tool Calls
    system_prompt = await _prepare_system_prompt(ctx)
    messages = await _prepare_messages(messages, ctx)

    # Run LangGraph
    async for chunk in _run_graph(ctx, messages, system_prompt):
        yield chunk


async def _prepare_system_prompt(ctx: AgentExecutionContext) -> str:
    """Enrich system prompt with skills and temporal context."""
    system_prompt = ctx.system_prompt

    # exec-10: Skill Injection
    try:
        from agent.skills.loader import load_skills, format_skills_for_prompt
        skills = load_skills(user_id=ctx.user_id)
        skills_text = format_skills_for_prompt(skills)
        if skills_text:
            system_prompt = f"{system_prompt}\n\n{skills_text}"
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

    return system_prompt


async def _prepare_messages(messages: list[dict], ctx: AgentExecutionContext) -> list[dict]:
    """Apply middleware to messages before graph execution."""
    # exec-10 Phase 5.5: Context Summarization
    try:
        from agent.middleware.summarization import apply_context_management
        messages = await apply_context_management(messages, model=ctx.model)
    except Exception:
        pass

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

    provider = os.environ.get("AGENT_PROVIDER", "anthropic").lower()
    if os.environ.get("AGENT_USE_LITELLM", "false").lower() == "true":
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
        "agent_class": getattr(ctx, "agent_class", "advisory"),
    }

    config = {"configurable": {"thread_id": ctx.thread_id}}

    try:
        text_id = "t1"
        yield sse(TextStartPacket(id=text_id))

        result = await graph.ainvoke(initial_state, config=config)

        final = result.get("final_response", "")
        if final:
            yield sse(TextDeltaPacket(id=text_id, text=final))

        for tr in result.get("tool_results", []):
            yield sse(ToolStartPacket(tool_name=tr["tool_name"], tool_call_id=tr["tool_call_id"]))
            if tr.get("error"):
                yield sse(ToolErrorPacket(tool_call_id=tr["tool_call_id"], error=tr["error"]))
            else:
                yield sse(ToolResultPacket(tool_call_id=tr["tool_call_id"], result=tr["result"]))

        yield sse(TextEndPacket(id=text_id))
        yield sse(MessageMetaPacket(metadata={
            "threadId": ctx.thread_id,
            "promptTokens": 0,  # TODO: extract from graph result
            "completionTokens": 0,
        }))
        yield sse(FinishPacket(finishReason="stop"))

    except Exception as e:
        yield sse(ErrorPacket(error=f"LangGraph error: {e}"))
