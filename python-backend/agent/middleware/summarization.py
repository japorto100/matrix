"""Deprecated — delegates to :mod:`agent.middleware.compaction` + :mod:`agent.middleware.compression`.

Phase-B P5 split this module into a mechanical-compaction stage
(:mod:`compaction`) and an LLM-compression stage (:mod:`compression`)
triggered separately by :class:`context.context_engine.ContextStage`.

This module remains as a shim so existing callers
(``apply_context_management``, ``should_summarize``, ``estimate_tokens``,
``offload_large_tool_results``, ``summarize_old_messages``) keep working
through 1–2 release cycles. New callers should import from ``compaction``
or ``compression`` directly.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from agent.middleware.compaction import (
    CHARS_PER_TOKEN,
    TOOL_RESULT_MAX_CHARS,
    compact,
    estimate_tokens,
    offload_large_tool_results,
)
from agent.middleware.compression import (
    KEEP_MESSAGES,
    SUMMARY_PROMPT,
    compress,
    summarize_old_messages,
)

logger = logging.getLogger(__name__)

THRESHOLD_FRACTION = float(os.environ.get("AGENT_SUMMARIZE_THRESHOLD", "0.7"))
SUMMARIZE_MODEL = os.environ.get("AGENT_SUMMARIZE_MODEL", "")

DEFAULT_MAX_TOKENS = 200_000


__all__ = [
    "CHARS_PER_TOKEN",
    "DEFAULT_MAX_TOKENS",
    "KEEP_MESSAGES",
    "SUMMARIZE_MODEL",
    "SUMMARY_PROMPT",
    "THRESHOLD_FRACTION",
    "TOOL_RESULT_MAX_CHARS",
    "apply_context_management",
    "compact",
    "compress",
    "estimate_tokens",
    "offload_large_tool_results",
    "should_summarize",
    "summarize_old_messages",
]


def should_summarize(messages: list[dict[str, Any]], model: str = "") -> bool:
    """Legacy threshold check. New code should use ``ContextEngine.stage_for``."""
    from agent.llm.model_metadata import get_model_context_window

    max_tokens = get_model_context_window(model) if model else DEFAULT_MAX_TOKENS
    threshold = int(max_tokens * THRESHOLD_FRACTION)
    current = estimate_tokens(messages)
    return current > threshold


async def apply_context_management(
    messages: list[dict[str, Any]],
    model: str = "",
) -> list[dict[str, Any]]:
    """Legacy 3-stage pipeline. New code should use the ContextEngine router.

    Kept as a shim so existing tests and callers keep passing. Internally
    delegates to compact() + compress() + final hard-truncate.
    """
    messages = compact(messages)

    if should_summarize(messages, model):
        logger.info(
            "Context threshold reached, compressing %d messages", len(messages)
        )
        messages = await compress(messages)

    from agent.llm.model_metadata import get_model_context_window

    max_tokens = get_model_context_window(model) if model else DEFAULT_MAX_TOKENS
    while estimate_tokens(messages) > max_tokens * 0.9 and len(messages) > 2:
        messages = messages[1:]

    return messages
