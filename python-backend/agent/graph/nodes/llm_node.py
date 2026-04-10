"""LLM Node — LangGraph Node, ein Pfad ueber LiteLLM (exec-16).

Client → LiteLLM Gateway → Provider. Model-Name bestimmt das Routing.
User API Key wird via extra_body={api_key: ...} durchgereicht.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agent.graph.state import AgentGraphState, ToolCall
from agent.llm_client import get_litellm_client
from agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


async def llm_node(state: AgentGraphState) -> dict[str, Any]:
    """Ruft das LLM auf und gibt tool_calls oder finale Antwort zurueck."""
    from agent.audit.logger import AuditAction, audit_duration, audit_log, audit_timer

    model = state["model"]
    messages = state["messages"]
    system_prompt = state["system_prompt"]
    api_key = state.get("api_key")
    thread_id = state.get("thread_id", "")
    iteration = state.get("iteration", 0)

    registry = ToolRegistry.load()
    tool_defs = [t.definition() for t in registry.all()]

    start = audit_timer()
    await audit_log(
        action=AuditAction.LLM_REQUEST,
        thread_id=thread_id,
        iteration=iteration,
        metadata={"model": model, "tool_count": len(tool_defs)},
    )

    client = get_litellm_client()

    # Tools: Anthropic format → OpenAI format
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": td["name"],
                "description": td.get("description", ""),
                "parameters": td.get("input_schema", {}),
            },
        }
        for td in tool_defs
    ]

    oai_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        if isinstance(msg.get("content"), str):
            oai_messages.append(msg)

    kwargs: dict[str, Any] = {"model": model, "messages": oai_messages}
    if openai_tools:
        kwargs["tools"] = openai_tools
    if api_key:
        kwargs["extra_body"] = {"api_key": api_key}

    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]

    token_usage = 0
    if response.usage:
        token_usage = (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)

    tool_calls: list[ToolCall] = []
    if choice.message.tool_calls:
        for tc in choice.message.tool_calls:
            tool_calls.append(
                ToolCall(
                    tool_call_id=tc.id,
                    tool_name=tc.function.name,
                    tool_input=json.loads(tc.function.arguments) if tc.function.arguments else {},
                )
            )

    # RL-2: Record token usage
    if token_usage > 0 and thread_id:
        from agent.consent.rate_limiter import get_rate_limiter
        get_rate_limiter().record_tokens(thread_id, token_usage)

    elapsed = audit_duration(start)
    await audit_log(
        action=AuditAction.LLM_RESPONSE,
        thread_id=thread_id,
        iteration=iteration,
        duration_ms=elapsed,
        success=True,
        metadata={"model": model, "done": not bool(tool_calls), "tool_calls_count": len(tool_calls), "token_usage": token_usage},
    )

    result: dict[str, Any] = {"tool_calls": tool_calls, "iteration": 1, "token_usage": token_usage}
    if tool_calls:
        result["messages"] = [{"role": "assistant", "content": choice.message.content or "", "tool_calls": choice.message.tool_calls}]
        result["done"] = False
    else:
        result["final_response"] = choice.message.content or ""
        result["done"] = True
        result["messages"] = [{"role": "assistant", "content": choice.message.content or ""}]

    return result
