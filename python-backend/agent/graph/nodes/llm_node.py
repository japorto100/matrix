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
from agent.resilience.rate_limit_tracker import RateLimitRegistry
from agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# Module-private rate-limit registry. Accessor pattern (mirror of
# agent.consent.rate_limiter.get_rate_limiter) lets tests swap the instance
# without monkey-patching the module global — see
# tests/agent/test_resilience_wiring.py for the pattern.
_rl_registry: RateLimitRegistry | None = None


def get_rate_limit_registry() -> RateLimitRegistry:
    """Return the process-wide RateLimitRegistry singleton.

    Lazy — first call constructs. Tests can reset via
    ``reset_rate_limit_registry()``.
    """
    global _rl_registry
    if _rl_registry is None:
        _rl_registry = RateLimitRegistry()
    return _rl_registry


def reset_rate_limit_registry() -> None:
    """Testing helper — drop the singleton so the next call rebuilds."""
    global _rl_registry
    _rl_registry = None


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
    # exec-hermes §3.5: rate-limit capture needs a caller identity. State
    # declares user_id but code paths don't always populate it — reserved
    # "anonymous" bucket key mirrors RateLimitBucket.user_id="" default so
    # anonymous traffic is separate from named-user buckets.
    user_id = state.get("user_id") or "anonymous"

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

        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            # exec-hermes §3.4 telemetry: annotate span with failover taxonomy
            # before re-raising. The outer runner catches + classifies again
            # for the ErrorPacket — here we add the classification to the trace
            # record so exec-17 Harness analysis sees the same dispatch.
            try:
                from agent.resilience.error_classifier import classify_error

                _cls = classify_error(exc)
                span.add_event(
                    "llm_error",
                    {
                        "reason": _cls.reason.value,
                        "recovery": _cls.recovery.value,
                        "retryable": _cls.retryable,
                        "status_code": _cls.status_code or -1,
                    },
                )
            except Exception:  # noqa: BLE001 — classification must never mask the real error
                pass
            raise
        choice = response.choices[0]

        # exec-hermes §3.5: capture x-ratelimit-* headers per-(user, provider-key).
        # provider_key_id uses _provider_label(model) as a Phase-1 proxy — coarse
        # but sufficient while exec-16 Credential-Pool is not yet wired
        # (the bucket-key tuple includes user_id so cross-user pollution is
        # already prevented). Swap for a hash of the real key-DB entry once
        # credential_pool lands.
        try:
            _rate_buckets = get_rate_limit_registry().capture_from_response(
                response,
                user_id=user_id,
                provider_key_id=_provider_label(model),
                provider=_provider_label(model),
            )
            # Surface minute-window requests bucket as span attributes so exec-17
            # Prom/OpenObserve dashboards can trace backpressure per request.
            _rpm_bucket = next(
                (b for b in _rate_buckets if b.window == "requests"), None
            )
            if _rpm_bucket is not None and _rpm_bucket.limit > 0:
                span.set_attribute("ratelimit.requests.limit", _rpm_bucket.limit)
                span.set_attribute("ratelimit.requests.remaining", _rpm_bucket.remaining)
                span.set_attribute("ratelimit.requests.usage_pct", _rpm_bucket.usage_pct)
        except Exception:  # noqa: BLE001 — rate-limit capture must never fail the call
            logger.debug("rate-limit capture skipped", exc_info=True)

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
