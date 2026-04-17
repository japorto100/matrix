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


def _detail_value(details: Any, key: str) -> int:
    if details is None:
        return 0
    if isinstance(details, dict):
        return int(details.get(key) or 0)
    return int(getattr(details, key, 0) or 0)


def _provider_label(model: str) -> str:
    parts = [part for part in str(model or "").split("/") if part]
    if not parts:
        return "litellm"
    if parts[0] == "openrouter":
        return "openrouter"
    if parts[0] in {"anthropic", "openai", "google", "deepseek", "groq", "mistral"}:
        return parts[0]
    return "litellm"


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

        # exec-17 / exec-context: Anthropic-style ephemeral cache on last messages (via LiteLLM).
        # Trifft u.a. openrouter/anthropic/claude-* und direkte claude IDs — nicht jedes OR-Modell.
        if _model_may_use_ephemeral_cache(model):
            _apply_anthropic_caching(oai_messages)

        kwargs: dict[str, Any] = {"model": model, "messages": oai_messages}
        if openai_tools:
            kwargs["tools"] = openai_tools

        extra_body: dict[str, Any] = {}
        if api_key:
            extra_body["api_key"] = api_key

        # exec-19 Stufe 5c: Reasoning/Thinking pipeline
        # LiteLLM handles per-provider mapping natively (v1.50+):
        # OpenAI → reasoning_effort, Anthropic → thinking block, DeepSeek → their format
        reasoning_effort = state.get("reasoning_effort")
        if reasoning_effort and reasoning_effort in ("low", "medium", "high"):
            kwargs["reasoning_effort"] = reasoning_effort

        if extra_body:
            kwargs["extra_body"] = extra_body

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        prompt_tokens = 0
        completion_tokens = 0
        reasoning_tokens = 0
        cached_tokens = 0
        token_usage = 0
        if response.usage:
            prompt_tokens = int(response.usage.prompt_tokens or 0)
            completion_tokens = int(response.usage.completion_tokens or 0)
            token_usage = prompt_tokens + completion_tokens
            cached_tokens = _detail_value(
                getattr(response.usage, "prompt_tokens_details", None),
                "cached_tokens",
            )
            reasoning_tokens = _detail_value(
                getattr(response.usage, "completion_tokens_details", None),
                "reasoning_tokens",
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
        if reasoning_effort:
            span.set_attribute("agent.reasoning.requested", reasoning_effort)
        usage_extra: dict[str, Any] = {}
        if response.usage:
            # LiteLLM / manche Provider: prompt_tokens_details.cached_tokens
            pt = getattr(response.usage, "prompt_tokens_details", None)
            if pt is not None:
                if hasattr(pt, "model_dump"):
                    usage_extra["prompt_tokens_details"] = pt.model_dump()
                elif isinstance(pt, dict):
                    usage_extra["prompt_tokens_details"] = pt
            ct = getattr(response.usage, "completion_tokens_details", None)
            if ct is not None:
                if hasattr(ct, "model_dump"):
                    usage_extra["completion_tokens_details"] = ct.model_dump()
                elif isinstance(ct, dict):
                    usage_extra["completion_tokens_details"] = ct

        span.track_generation(
            name="agent.llm_call",
            model=model,
            input=str(oai_messages[-1].get("content", ""))[:5000]
            if oai_messages
            else "",
            output=choice.message.content[:5000] if choice.message.content else "",
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": token_usage,
                **usage_extra,
            },
            metadata={"thread_id": thread_id, "iteration": iteration},
        )

        total_prompt_tokens = int(state.get("prompt_tokens", 0) or 0) + prompt_tokens
        total_completion_tokens = int(state.get("completion_tokens", 0) or 0) + completion_tokens
        total_reasoning_tokens = int(state.get("reasoning_tokens", 0) or 0) + reasoning_tokens
        total_cached_tokens = int(state.get("cached_tokens", 0) or 0) + cached_tokens
        total_token_usage = int(state.get("token_usage", 0) or 0) + token_usage
        resolved_model = str(getattr(response, "model", "") or model)

        result: dict[str, Any] = {
            "tool_calls": tool_calls,
            "iteration": 1,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "reasoning_tokens": total_reasoning_tokens,
            "cached_tokens": total_cached_tokens,
            "token_usage": total_token_usage,
            "llm_provider": _provider_label(resolved_model),
            "llm_model": resolved_model,
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




def _model_may_use_ephemeral_cache(model: str) -> bool:
    """True wenn LiteLLM/Upstream Anthropic-style cache_control unterstuetzt (heuristisch)."""
    m = model.lower()
    if "claude" in m or "anthropic" in m:
        return True
    # OpenRouter: openrouter/anthropic/claude-... — bereits durch claude/anthropic abgedeckt
    return False


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
