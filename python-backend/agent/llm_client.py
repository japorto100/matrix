"""Shared LiteLLM Client — einziger OpenAI SDK Client im Agent.

Alle LLM-Calls gehen hierueber → LiteLLM Gateway → Provider.
Konfiguration: LITELLM_BASE_URL (default: http://localhost:4000)
"""

from __future__ import annotations

import os
from functools import lru_cache

from openai import AsyncOpenAI


@lru_cache(maxsize=1)
def get_litellm_client() -> AsyncOpenAI:
    """Singleton OpenAI Client der auf LiteLLM zeigt."""
    base_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
    return AsyncOpenAI(base_url=base_url, api_key="sk-litellm")
