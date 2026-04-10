"""Langfuse LLM Tracker — enriches OTel spans with LLM-specific metadata (exec-17 Phase 3).

Activated via LANGFUSE_ENABLED=true + LANGFUSE_PUBLIC_KEY/SECRET_KEY.
When disabled, all functions are no-ops (zero overhead).

Complements OTel traces (Phase 1-2) with Langfuse-specific features:
- Prompt/Response tracking per generation
- Token cost breakdown per model
- Evaluation scores (Phase 5)

Strategy (based on PentAGI analysis):
  PentAGI uses a massive auto-generated Go Langfuse client (20+ files).
  We use the official Python SDK instead — thin wrapper, same features.
  OTel Collector fan-out to Langfuse provides base span data automatically.
  This module adds LLM-specific enrichments that OTel cannot express.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def _get_langfuse():
    """Lazy singleton — returns None if Langfuse is disabled or unconfigured."""
    if os.getenv("LANGFUSE_ENABLED", "").strip().lower() != "true":
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except Exception:
        return None


def track_generation(
    *,
    name: str,
    model: str,
    input: str,
    output: str,
    usage: dict[str, int],
    metadata: dict[str, Any] | None = None,
) -> None:
    """Track an LLM generation in Langfuse.

    No-op when LANGFUSE_ENABLED is not true.
    Called from llm_node.py after each LLM response.
    """
    lf = _get_langfuse()
    if lf is None:
        return

    try:
        trace = lf.trace(name=name, metadata=metadata or {})
        trace.generation(
            name=f"{name}.llm",
            model=model,
            input=input[:5000],
            output=output[:5000],
            usage=usage,
            metadata=metadata or {},
        )
    except Exception:
        pass  # Langfuse failure must not break the agent


def flush() -> None:
    """Flush pending Langfuse events. Call on shutdown."""
    lf = _get_langfuse()
    if lf is not None:
        try:
            lf.flush()
        except Exception:
            pass
