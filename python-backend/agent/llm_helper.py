"""Shared LLM Helper — Utility-Calls ueber LiteLLM.

Fuer Nicht-Graph LLM-Calls: Summarization, Skill-Generation, etc.
Utility-Calls nutzen AGENT_DEFAULT_UTILITY_MODEL als Fallback.
"""

from __future__ import annotations

import json
import logging
import os

from agent.llm_client import get_litellm_client

logger = logging.getLogger(__name__)


async def llm_call(
    prompt: str,
    model: str | None = None,
    max_tokens: int = 2048,
    system: str | None = None,
    api_key: str | None = None,
) -> str:
    """LLM-Call ueber LiteLLM. Model-Name bestimmt den Provider.

    Wenn kein Model: AGENT_DEFAULT_UTILITY_MODEL aus ENV (Summarization etc.).
    """
    client = get_litellm_client()

    if not model:
        model = os.environ.get("AGENT_DEFAULT_UTILITY_MODEL", "")
    if not model:
        raise ValueError("Kein Model fuer Utility-Call. Setze AGENT_DEFAULT_UTILITY_MODEL in .env")

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if api_key:
        kwargs["extra_body"] = {"api_key": api_key}

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def extract_json(text: str) -> dict:
    """Extrahiert JSON aus LLM-Response (auch wenn in Code-Block)."""
    if "```" in text:
        text = text.split("```")[1].removeprefix("json").strip()
    return json.loads(text)
