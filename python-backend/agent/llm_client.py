"""Shared LiteLLM Client — einziger OpenAI SDK Client im Agent.

Alle LLM-Calls gehen hierueber → LiteLLM Gateway → Provider (OpenRouter-Upstreams
ueber Model-String `openrouter/...`). Prompt-Caching / Extra-Parameter:
provider-agnostisch in den Call-Sites (z. B. `agent/graph/nodes/llm_node.py`),
nicht parallel ein zweites Provider-SDK — siehe specs/execution/exec-context.md.

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
