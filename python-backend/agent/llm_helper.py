"""Shared LLM Helper — provider-agnostischer LLM-Aufruf (exec-10 Refactor).

Alle LLM-Calls im Agent-System muessen diesen Helper nutzen statt
AsyncAnthropic/AsyncOpenAI direkt zu importieren.

Respektiert: AGENT_PROVIDER, AGENT_USE_LITELLM, OPENAI_BASE_URL
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def llm_call(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 2048,
    system: str | None = None,
) -> str:
    """Provider-agnostischer LLM-Call. Gibt Text-Response zurueck.

    Routing:
      AGENT_USE_LITELLM=true → LiteLLM (multi-provider)
      AGENT_PROVIDER=anthropic → Anthropic SDK
      AGENT_PROVIDER=openai/openai-compatible → OpenAI SDK

    Args:
        prompt: User-Message
        model: Model override (default: aus ENV)
        max_tokens: Max Output Tokens
        system: Optional System-Prompt

    Returns:
        LLM Text-Response als String.
    """
    provider = os.environ.get("AGENT_PROVIDER", "anthropic").lower()
    use_litellm = os.environ.get("AGENT_USE_LITELLM", "false").lower() == "true"

    if model is None:
        default = "claude-haiku-4-5" if provider == "anthropic" else "gpt-4o-mini"
        model = os.environ.get("AGENT_UTILITY_MODEL", default)

    if use_litellm:
        return await _call_litellm(prompt, model, max_tokens, system)
    elif provider in ("openai", "openai-compatible"):
        return await _call_openai(prompt, model, max_tokens, system, provider)
    else:
        return await _call_anthropic(prompt, model, max_tokens, system)


async def _call_anthropic(prompt: str, model: str, max_tokens: int, system: str | None) -> str:
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic()
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    response = await client.messages.create(**kwargs)
    return response.content[0].text if response.content else ""


async def _call_openai(prompt: str, model: str, max_tokens: int, system: str | None, provider: str) -> str:
    from openai import AsyncOpenAI
    base_url = os.environ.get("OPENAI_BASE_URL") if provider == "openai-compatible" else None
    client = AsyncOpenAI(base_url=base_url)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = await client.chat.completions.create(
        model=model, max_tokens=max_tokens, messages=messages,
    )
    return response.choices[0].message.content or ""


async def _call_litellm(prompt: str, model: str, max_tokens: int, system: str | None) -> str:
    import litellm
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    response = await litellm.acompletion(
        model=model, max_tokens=max_tokens, messages=messages,
    )
    return response.choices[0].message.content or ""


def extract_json(text: str) -> dict:
    """Extrahiert JSON aus LLM-Response (auch wenn in Code-Block)."""
    if "```" in text:
        text = text.split("```")[1].removeprefix("json").strip()
    return json.loads(text)
