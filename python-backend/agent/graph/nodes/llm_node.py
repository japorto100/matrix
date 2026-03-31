"""LLM Node — provider-agnostischer LLM Call als LangGraph Node.

Unified Node statt 3 separate Loop-Funktionen.
Unterstuetzt: Anthropic, OpenAI, OpenAI-compatible, LiteLLM.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from agent.graph.state import AgentGraphState, ToolCall
from agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


async def llm_node(state: AgentGraphState) -> dict[str, Any]:
    """Ruft das LLM auf und gibt tool_calls oder finale Antwort zurueck."""
    provider = state["provider"]
    model = state["model"]
    messages = state["messages"]
    system_prompt = state["system_prompt"]
    reasoning_effort = state.get("reasoning_effort")

    # Tools laden
    registry = ToolRegistry.load()
    tool_defs = [t.definition() for t in registry.all()]

    if provider == "anthropic":
        return await _call_anthropic(model, system_prompt, messages, tool_defs, reasoning_effort)
    elif provider in ("openai", "openai-compatible"):
        return await _call_openai(model, system_prompt, messages, tool_defs, reasoning_effort, provider)
    elif provider == "litellm":
        return await _call_litellm(model, system_prompt, messages, tool_defs, reasoning_effort)
    else:
        return {"final_response": f"Unknown provider: {provider}", "done": True, "tool_calls": []}


async def _call_anthropic(
    model: str,
    system_prompt: str,
    messages: list[dict],
    tool_defs: list[dict],
    reasoning_effort: str | None,
) -> dict[str, Any]:
    """Anthropic Claude API call."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": 8192,
        "system": system_prompt,
        "messages": messages,
    }

    if tool_defs:
        kwargs["tools"] = tool_defs

    # Reasoning effort → Anthropic thinking
    if reasoning_effort and reasoning_effort != "medium":
        budget = {"low": 2048, "high": 16384}.get(reasoning_effort, 8192)
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}

    response = await client.messages.create(**kwargs)

    # Parse response
    tool_calls: list[ToolCall] = []
    text_parts: list[str] = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(
                    tool_call_id=block.id,
                    tool_name=block.name,
                    tool_input=block.input if isinstance(block.input, dict) else {},
                )
            )

    result: dict[str, Any] = {"tool_calls": tool_calls, "iteration": 1}

    if tool_calls:
        # Add assistant message with tool_use blocks to history
        result["messages"] = [{"role": "assistant", "content": response.content}]
        result["done"] = False
    else:
        result["final_response"] = "".join(text_parts)
        result["done"] = True
        result["messages"] = [{"role": "assistant", "content": "".join(text_parts)}]

    return result


async def _call_openai(
    model: str,
    system_prompt: str,
    messages: list[dict],
    tool_defs: list[dict],
    reasoning_effort: str | None,
    provider: str,
) -> dict[str, Any]:
    """OpenAI / OpenAI-compatible API call."""
    from openai import AsyncOpenAI

    base_url = os.environ.get("OPENAI_BASE_URL") if provider == "openai-compatible" else None
    client = AsyncOpenAI(base_url=base_url)

    # Convert Anthropic tool format to OpenAI format
    openai_tools = []
    for td in tool_defs:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": td["name"],
                "description": td.get("description", ""),
                "parameters": td.get("input_schema", {}),
            },
        })

    oai_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        if isinstance(msg.get("content"), str):
            oai_messages.append(msg)

    kwargs: dict[str, Any] = {"model": model, "messages": oai_messages}
    if openai_tools:
        kwargs["tools"] = openai_tools

    response = await client.chat.completions.create(**kwargs)
    choice = response.choices[0]

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

    result: dict[str, Any] = {"tool_calls": tool_calls, "iteration": 1}

    if tool_calls:
        result["messages"] = [{"role": "assistant", "content": choice.message.content or "", "tool_calls": choice.message.tool_calls}]
        result["done"] = False
    else:
        result["final_response"] = choice.message.content or ""
        result["done"] = True
        result["messages"] = [{"role": "assistant", "content": choice.message.content or ""}]

    return result


async def _call_litellm(
    model: str,
    system_prompt: str,
    messages: list[dict],
    tool_defs: list[dict],
    reasoning_effort: str | None,
) -> dict[str, Any]:
    """LiteLLM multi-provider call (delegates to _call_openai with litellm)."""
    # LiteLLM uses OpenAI-compatible interface
    return await _call_openai(model, system_prompt, messages, tool_defs, reasoning_effort, "openai-compatible")
