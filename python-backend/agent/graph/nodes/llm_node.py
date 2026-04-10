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
    from agent.tracing import turn_span

    model = state["model"]
    messages = state["messages"]
    system_prompt = state["system_prompt"]
    api_key = state.get("api_key")
    thread_id = state.get("thread_id", "")
    iteration = state.get("iteration", 0)

    registry = ToolRegistry.load()
    tool_defs = [t.definition() for t in registry.all()]

    with turn_span("llm_call", model, iteration) as span:
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

        # exec-17 Phase 6: Anthropic ephemeral caching on last 3 messages
        # Saves 60-90% prompt tokens on multi-turn (from Meta-Harness artifact)
        if "claude" in model.lower() or "anthropic" in model.lower():
            _apply_anthropic_caching(oai_messages)

        kwargs: dict[str, Any] = {"model": model, "messages": oai_messages}
        if openai_tools:
            kwargs["tools"] = openai_tools
        if api_key:
            kwargs["extra_body"] = {"api_key": api_key}

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        token_usage = 0
        if response.usage:
            token_usage = (response.usage.prompt_tokens or 0) + (
                response.usage.completion_tokens or 0
            )

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        tool_call_id=tc.id,
                        tool_name=tc.function.name,
                        tool_input=json.loads(tc.function.arguments)
                        if tc.function.arguments
                        else {},
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
            input_data=str(oai_messages[-1].get("content", ""))[:2000]
            if oai_messages
            else "",
            output_data=choice.message.content[:2000] if choice.message.content else "",
            metadata={
                "model": model,
                "done": not bool(tool_calls),
                "tool_calls_count": len(tool_calls),
                "token_usage": token_usage,
            },
        )

        # exec-17: OTel + Langfuse via unified AgentSpan
        span.set_attribute("agent.tool_calls_count", len(tool_calls))
        span.track_generation(
            name="agent.llm_call",
            model=model,
            input=str(oai_messages[-1].get("content", ""))[:5000]
            if oai_messages
            else "",
            output=choice.message.content[:5000] if choice.message.content else "",
            usage={
                "prompt_tokens": response.usage.prompt_tokens or 0
                if response.usage
                else 0,
                "completion_tokens": response.usage.completion_tokens or 0
                if response.usage
                else 0,
                "total_tokens": token_usage,
            },
            metadata={"thread_id": thread_id, "iteration": iteration},
        )

        result: dict[str, Any] = {
            "tool_calls": tool_calls,
            "iteration": 1,
            "token_usage": token_usage,
        }
        if tool_calls:
            result["messages"] = [
                {
                    "role": "assistant",
                    "content": choice.message.content or "",
                    "tool_calls": choice.message.tool_calls,
                }
            ]
            result["done"] = False
        else:
            result["final_response"] = choice.message.content or ""
            result["done"] = True
            result["messages"] = [
                {"role": "assistant", "content": choice.message.content or ""}
            ]

        return result


def _apply_anthropic_caching(messages: list[dict[str, Any]]) -> None:
    """Add ephemeral cache_control to last 3 messages for Anthropic models.

    From Meta-Harness TerminalBench artifact (anthropic_caching.py).
    Saves 60-90% prompt tokens on multi-turn conversations.
    """
    for i in range(max(0, len(messages) - 3), len(messages)):
        msg = messages[i]
        if isinstance(msg.get("content"), str):
            msg["content"] = [
                {
                    "type": "text",
                    "text": msg["content"],
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        elif isinstance(msg.get("content"), list):
            for item in msg["content"]:
                if isinstance(item, dict) and "type" in item:
                    item["cache_control"] = {"type": "ephemeral"}
