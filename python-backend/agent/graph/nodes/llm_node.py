"""LLM Node — LangGraph Node, ein Pfad ueber LiteLLM (exec-16).

Client → LiteLLM Gateway → Provider. Model-Name bestimmt das Routing.
User API Key wird via extra_body={api_key: ...} durchgereicht.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from agent.errors import CredentialExhaustedError
from agent.graph.state import AgentGraphState, ToolCall
from agent.llm.provider_capabilities import model_capabilities
from agent.llm.request_telemetry import (
    build_request_telemetry,
    telemetry_span_attributes,
)
from agent.llm_client import get_litellm_client
from agent.resilience.credential_pool import (
    Credential,
    apply_recovery,
    get_credential_pool,
)
from agent.resilience.rate_limit_tracker import RateLimitRegistry
from agent.routing.delegation_policy import build_route_decision_metadata
from agent.runtime_events import make_runtime_event, runtime_event_span_attributes
from agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_TEXTUAL_TOOL_CALL_RE = re.compile(
    r"<\s*(tool_call|function_call|tool_use|action)\s*>.*?</\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)


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


def _resolve_model_name(model: str | None) -> str:
    return (
        str(model or "").strip()
        or os.environ.get("AGENT_DEFAULT_MODEL", "").strip()
        or os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "").strip()
    )


def _max_output_tokens_from_env() -> int | None:
    raw = os.environ.get("AGENT_MAX_OUTPUT_TOKENS", "4096").strip()
    if not raw:
        return 4096
    try:
        value = int(raw)
    except ValueError:
        return 4096
    return value if value > 0 else None


def _clean_assistant_content(content: str) -> str:
    """Strip provider-leaked reasoning/tool-call markers from assistant text."""
    text = str(content or "")
    lowered = text.lower()
    for marker in ("assistantfinal", "assistant_final", "<|assistant|>final"):
        idx = lowered.rfind(marker)
        if idx >= 0:
            text = text[idx + len(marker) :].lstrip(" :\n\r\t")
            break

    cleaned = _TEXTUAL_TOOL_CALL_RE.sub("", text).strip()
    if cleaned:
        return cleaned
    if text != cleaned and _TEXTUAL_TOOL_CALL_RE.search(text):
        return "Done."
    return text


async def llm_node(state: AgentGraphState) -> dict[str, Any]:
    """Ruft das LLM auf und gibt tool_calls oder finale Antwort zurueck."""
    from agent.audit.logger import AuditAction, audit_duration, audit_log, audit_timer
    from agent.tracing import turn_span

    model = _resolve_model_name(state.get("model"))
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

    # ADR-001 P1: smart-routing decision is now produced by router_node
    # (runs once BEFORE llm_call per graph construction). Read the
    # decision outputs from state for span-attributes + logging. Default
    # values from graph init make this safe for ad-hoc invocations that
    # skip the router (tests, harness).
    routing_reason = state.get("routing_reason") or "not_evaluated"
    routing_used = bool(state.get("routing_used"))
    routing_picked_model = state.get("routing_picked_model") or ""

    configured_tool_defs = state.get("tool_definitions")
    if configured_tool_defs is None:
        registry = ToolRegistry.load()
        tool_defs = [t.definition() for t in registry.all()]
    else:
        tool_defs = list(configured_tool_defs)

    with turn_span("llm_call", model, iteration) as span:
        span.set_attribute("llm.routing_reason", routing_reason)
        span.set_attribute("llm.routing_used", routing_used)
        if routing_picked_model:
            span.set_attribute("llm.routing_picked", routing_picked_model)
        # ADR-002: LLM_REQUEST audit_log entfernt — redundant mit diesem
        # span (model/iteration bereits getragen). tool_count als span-attr
        # statt als audit-metadata. LLM_RESPONSE bleibt für content trail.
        span.set_attribute("agent.tool_count", len(tool_defs))
        start = audit_timer()

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

        capabilities = model_capabilities(model)
        known_capabilities = bool(capabilities.get("known_to_litellm"))
        kwargs: dict[str, Any] = {"model": model, "messages": oai_messages}
        if openai_tools and not _known_false(
            known_capabilities,
            capabilities.get("supports_tools"),
        ):
            kwargs["tools"] = openai_tools
        elif openai_tools:
            span.add_event(
                "provider_field_omitted",
                {
                    "field": "tools",
                    "reason": "unsupported_by_model_capabilities",
                    "model": model,
                },
            )
        max_output_tokens = _max_output_tokens_from_env()
        if max_output_tokens is not None:
            kwargs["max_tokens"] = max_output_tokens

        # exec-hermes Phase-B P1: consult CredentialPool BEFORE the LLM call.
        # When a usable credential exists we pass it through extra_body
        # (overriding any state.api_key fallback) AND use its opaque
        # key_id as the rate-limit bucket identifier — that gives us
        # per-key isolation instead of per-provider coarse-grain.
        # When acquire() returns None the key is blocked (rate-limited
        # / auth-rejected) — surface CredentialExhaustedError so the
        # runner produces a user-facing ErrorPacket rather than silently
        # sending a broken key through.
        credential: Credential | None = None
        try:
            credential = await get_credential_pool().acquire(
                user_id=user_id,
                provider=_provider_label(model),
            )
        except Exception:  # noqa: BLE001 — pool must never break the call
            logger.debug("credential_pool.acquire skipped", exc_info=True)

        extra_body: dict[str, Any] = {}
        if credential is not None:
            extra_body["api_key"] = credential.api_key
            span.set_attribute("credential.key_id", credential.key_id)
        elif api_key:
            # Legacy fallback — no pool entry found but the state has
            # a prefetched api_key. Happens on code-paths that haven't
            # yet migrated to the credential-pool flow (tests, harness).
            extra_body["api_key"] = api_key
        else:
            # Neither pool nor state has a key. If user is configured
            # to need one, upstream will 401; let the call go and surface
            # the provider error. Anonymous routes without user creds
            # (dev mode) are allowed to fall through.
            if user_id != "anonymous":
                span.add_event(
                    "credential_exhausted",
                    {"user_id": user_id, "provider": _provider_label(model)},
                )
                raise CredentialExhaustedError(
                    user_id=user_id,
                    provider=_provider_label(model),
                    reason="pool.acquire returned None",
                )

        # exec-19 Stufe 5c: Reasoning/Thinking pipeline
        # LiteLLM handles per-provider mapping natively (v1.50+):
        # OpenAI → reasoning_effort, Anthropic → thinking block, DeepSeek → their format
        reasoning_effort = state.get("reasoning_effort")
        if reasoning_effort and reasoning_effort in ("low", "medium", "high"):
            if not _known_false(
                known_capabilities,
                capabilities.get("supports_reasoning_effort"),
            ):
                kwargs["reasoning_effort"] = reasoning_effort
            else:
                span.add_event(
                    "provider_field_omitted",
                    {
                        "field": "reasoning_effort",
                        "reason": "unsupported_by_model_capabilities",
                        "model": model,
                    },
                )

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
                # exec-hermes Phase-B P1: dispatch credential-pool recovery
                # (rate_limit → 1h cooldown, billing → 24h, auth → mark_auth_failed,
                # overloaded/server_error → 5min). apply_recovery is a no-op
                # for non-credential classifications (context-overflow etc.).
                if credential is not None:
                    try:
                        await apply_recovery(
                            get_credential_pool(),
                            credential,
                            _cls,
                        )
                    except Exception:  # noqa: BLE001 — recovery failure mustn't hide root cause
                        logger.debug("apply_recovery failed", exc_info=True)
            except Exception:  # noqa: BLE001 — classification must never mask the real error
                pass
            raise
        choice = response.choices[0]
        assistant_content = _clean_assistant_content(choice.message.content or "")

        # exec-hermes §3.5: capture x-ratelimit-* headers per-(user, provider-key).
        # exec-hermes Phase-B P1: when a CredentialPool credential is available,
        # use its opaque key_id as the rate-limit bucket identifier. This gives
        # us per-key isolation (same user rotating between 2 keys = separate
        # buckets) instead of the coarse per-provider grain. Fallback to
        # _provider_label(model) for legacy paths without a pool credential.
        _bucket_key_id = (
            credential.key_id if credential is not None else _provider_label(model)
        )
        try:
            _rate_buckets = get_rate_limit_registry().capture_from_response(
                response,
                user_id=user_id,
                provider_key_id=_bucket_key_id,
                provider=_provider_label(model),
            )
            # Surface minute-window requests bucket as span attributes so exec-17
            # Prom/OpenObserve dashboards can trace backpressure per request.
            _rpm_bucket = next(
                (b for b in _rate_buckets if b.window == "requests"), None
            )
            if _rpm_bucket is not None and _rpm_bucket.limit > 0:
                span.set_attribute("ratelimit.requests.limit", _rpm_bucket.limit)
                span.set_attribute(
                    "ratelimit.requests.remaining", _rpm_bucket.remaining
                )
                span.set_attribute(
                    "ratelimit.requests.usage_pct", _rpm_bucket.usage_pct
                )
        except Exception:  # noqa: BLE001 — rate-limit capture must never fail the call
            logger.debug("rate-limit capture skipped", exc_info=True)

        # exec-hermes Phase-B P1: the call succeeded — mark the credential
        # healthy again. Resets any lingering exhausted/auth_failed state
        # (e.g. a provider just recovered from a 429 backoff). No-op for
        # credentials in ok-state.
        if credential is not None:
            try:
                await get_credential_pool().mark_success(credential)
            except Exception:  # noqa: BLE001 — bookkeeping mustn't break the response path
                logger.debug("credential_pool.mark_success failed", exc_info=True)

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

        resolved_model = str(getattr(response, "model", "") or model)
        provider = _provider_label(resolved_model)
        previous_telemetry = None
        prior_request_telemetry = state.get("request_telemetry") or []
        if prior_request_telemetry:
            previous_telemetry = prior_request_telemetry[-1]
        request_telemetry = build_request_telemetry(
            provider=provider,
            model=resolved_model,
            router=str(state.get("runner_variant") or "unknown"),
            thread_id=thread_id,
            iteration=iteration,
            messages=oai_messages,
            tools=openai_tools,
            usage=response.usage,
            previous=previous_telemetry,
            metadata={
                "routing_reason": routing_reason,
                "routing_used": routing_used,
                "tool_count": len(openai_tools),
                "capabilities_known": known_capabilities,
            },
        )
        for key, value in telemetry_span_attributes(request_telemetry).items():
            span.set_attribute(key, value)

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

        tool_names = [tc["tool_name"] for tc in tool_calls]
        await audit_log(
            action=AuditAction.ROUTE_DECISION,
            thread_id=thread_id,
            iteration=iteration,
            success=True,
            metadata=build_route_decision_metadata(
                runner=state.get("runner_variant") or "unknown",
                tool_names=tool_names,
                routing_reason=routing_reason,
                routing_used=routing_used,
                routing_picked_model=routing_picked_model,
                max_spawn_depth=0,
                memory_scope=str(state.get("memory_scope") or "current_user"),
            ),
        )

        # RL-2: Record token usage
        if token_usage > 0 and thread_id:
            from agent.consent.rate_limiter import get_rate_limiter

            get_rate_limiter().record_tokens(thread_id, token_usage)

        # P4: emit cost + cache-hit span-attributes so InsightsEngine can
        # aggregate without re-running LiteLLM per row. Fail-soft — a bad
        # pricing lookup must never break the LLM turn.
        try:
            from agent.billing.usage_pricing import (
                estimate_usage_cost,
                usage_from_litellm,
            )

            usage_dict = (
                response.usage.model_dump()
                if hasattr(response.usage, "model_dump")
                else None
            )
            canonical = usage_from_litellm(usage_dict)
            cost = estimate_usage_cost(model, canonical)
            span.set_attribute("llm.input_tokens", canonical.input_tokens)
            span.set_attribute("llm.cache_read_tokens", canonical.cache_read_tokens)
            span.set_attribute("llm.cache_write_tokens", canonical.cache_write_tokens)
            span.set_attribute("llm.reasoning_tokens", canonical.reasoning_tokens)
            span.set_attribute("llm.cost_status", cost.status)
            if cost.amount_usd is not None:
                span.set_attribute("llm.cost_usd", str(cost.amount_usd))
            if cost.source:
                span.set_attribute("llm.cost_source", cost.source)
        except Exception:  # noqa: BLE001
            logger.debug("cost-estimation failed", exc_info=True)

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
            output_data=assistant_content[:2000],
            metadata={
                "model": model,
                "done": not bool(tool_calls),
                "tool_calls_count": len(tool_calls),
                "token_usage": token_usage,
                "content_cleaned": assistant_content != (choice.message.content or ""),
                "request_telemetry": request_telemetry,
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
            output=assistant_content[:5000],
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": token_usage,
                **usage_extra,
            },
            metadata={"thread_id": thread_id, "iteration": iteration},
        )

        total_prompt_tokens = int(state.get("prompt_tokens", 0) or 0) + prompt_tokens
        total_completion_tokens = (
            int(state.get("completion_tokens", 0) or 0) + completion_tokens
        )
        total_reasoning_tokens = (
            int(state.get("reasoning_tokens", 0) or 0) + reasoning_tokens
        )
        total_cached_tokens = int(state.get("cached_tokens", 0) or 0) + cached_tokens
        total_token_usage = int(state.get("token_usage", 0) or 0) + token_usage
        runtime_event = make_runtime_event(
            kind="llm",
            status="completed",
            name="llm_call",
            summary=f"{provider}:{resolved_model}",
            thread_id=thread_id,
            turn=iteration,
            metadata={
                "request_telemetry": request_telemetry,
                "tool_calls_count": len(tool_calls),
                "done": not bool(tool_calls),
            },
        )
        for key, value in runtime_event_span_attributes(runtime_event).items():
            span.set_attribute(key, value)

        result: dict[str, Any] = {
            "tool_calls": tool_calls,
            "iteration": 1,
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "reasoning_tokens": total_reasoning_tokens,
            "cached_tokens": total_cached_tokens,
            "token_usage": total_token_usage,
            "request_telemetry": [request_telemetry],
            "runtime_events": [runtime_event],
            "llm_provider": provider,
            "llm_model": resolved_model,
        }
        if tool_calls:
            result["messages"] = [
                {
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": choice.message.tool_calls,
                }
            ]
            result["done"] = False
        else:
            result["final_response"] = assistant_content
            result["done"] = True
            result["messages"] = [{"role": "assistant", "content": assistant_content}]

        return result


def _known_false(known_capabilities: bool, value: Any) -> bool:
    """Return True only when model metadata explicitly says a field is unsupported."""
    return known_capabilities and value is False


def _model_may_use_ephemeral_cache(model: str) -> bool:
    """True wenn LiteLLM/Upstream Anthropic-style cache_control unterstuetzt (heuristisch)."""
    m = model.lower()
    if "claude" in m or "anthropic" in m:
        return True
    # OpenRouter: openrouter/anthropic/claude-... — bereits durch claude/anthropic abgedeckt
    return False


def _mark_cache_control(msg: dict[str, Any]) -> None:
    """Attach ephemeral cache_control to every content part of one message."""
    content = msg.get("content")
    if isinstance(content, str):
        msg["content"] = [
            {
                "type": "text",
                "text": content,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and "type" in item:
                item["cache_control"] = {"type": "ephemeral"}


def _apply_anthropic_caching(messages: list[dict[str, Any]]) -> None:
    """Add ephemeral cache_control for Anthropic models.

    Plan exec-hermes §4.5 requires ``System + letzte 3 non-system messages``
    — four breakpoints. The system prompt is always ``messages[0]`` (see
    ``llm_node`` at the top) and must get ``cache_control`` unconditionally
    so every long-session turn reuses the cached system prefix. The
    rolling window then covers the last three *non-system* messages.

    Saves 60–90% prompt tokens on multi-turn Anthropic conversations.
    """
    if not messages:
        return

    # 1. System prompt — always cached (unconditional breakpoint).
    system_idx: int | None = None
    if messages[0].get("role") == "system":
        system_idx = 0
        _mark_cache_control(messages[0])

    # 2. Last-3 rolling window over NON-system messages.
    non_system_positions = [i for i, m in enumerate(messages) if i != system_idx]
    for idx in non_system_positions[-3:]:
        _mark_cache_control(messages[idx])
