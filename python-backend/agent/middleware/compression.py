"""Context compression — LLM-backed lossy summarisation (P5 split).

Compression is the expensive, **lossy** side of context-management: old
messages are replaced with an LLM-generated summary. Triggered by
:data:`context.context_engine.ContextStage.compression` (~95% of the
context window) or :data:`ContextStage.emergency`.

Data-loss gate — ``on_pre_compress``:
Before compressing, we notify the :class:`MemoryManager` so mempalace /
hindsight can persist the soon-to-be-lost messages. This is awaited with
a 500ms timeout (exec-context §6.3 contract) so a slow mempalace doesn't
stall the LLM turn indefinitely. A timeout or missing manager emits an
``archive-miss`` span-event and compression proceeds — we prefer to lose
an archive entry over stalling the user-facing response.

Observational consumers (metrics, audit-log, exec-17) receive a
``pre_compression`` span-event, fire-and-forget.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


KEEP_MESSAGES = int(os.environ.get("AGENT_SUMMARIZE_KEEP_MESSAGES", "20"))
SUMMARIZE_MODEL = os.environ.get("AGENT_SUMMARIZE_MODEL", "")
PRE_COMPRESS_TIMEOUT_S = float(
    os.environ.get("AGENT_PRE_COMPRESS_TIMEOUT_S", "0.5")
)


SUMMARY_PROMPT = """Summarize the following conversation history concisely.
Preserve: key decisions, tool results, important facts, user preferences.
Discard: greetings, repeated questions, verbose tool outputs.
Output a single paragraph summary.

Conversation:
{conversation}"""


__all__ = [
    "KEEP_MESSAGES",
    "PRE_COMPRESS_TIMEOUT_S",
    "summarize_old_messages",
    "compress",
    "notify_pre_compression",
]


async def notify_pre_compression(
    messages_to_archive: list[dict[str, Any]],
    *,
    user_id: str | None = None,
    bank_id: str | None = None,
) -> list[str]:
    """Invoke ``MemoryManager.on_pre_compress`` with a bounded timeout.

    This is the **data-preserving** pre-compression hook (exec-context
    §6.3). Memory manager failure or timeout does not abort the
    compression — it is logged as an archive-miss and we move on.

    When ``user_id`` or ``bank_id`` is absent the hook is skipped (providers
    require per-user scoping for verbatim-archive). Returns the list of
    snippets emitted by providers that chose to re-inject a post-compact
    digest (usually empty).
    """
    if not user_id or not bank_id:
        logger.debug("pre_compression: missing user_id/bank_id, skipping archive")
        return []

    try:
        from memory_fusion.memory_provider import get_memory_manager

        manager = get_memory_manager()
    except Exception:  # noqa: BLE001
        manager = None

    if manager is None:
        logger.debug("pre_compression: no MemoryManager, skipping archive call")
        return []

    try:
        return await asyncio.wait_for(
            manager.on_pre_compress(
                messages_to_archive, user_id=user_id, bank_id=bank_id,
            ),
            timeout=PRE_COMPRESS_TIMEOUT_S,
        )
    except TimeoutError:
        logger.warning(
            "pre_compression: MemoryManager.on_pre_compress timed out after %.2fs — archive miss",
            PRE_COMPRESS_TIMEOUT_S,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("pre_compression: archive hook raised %s — archive miss", exc)
    return []


async def summarize_old_messages(
    messages: list[dict[str, Any]],
    keep: int = KEEP_MESSAGES,
    *,
    user_id: str | None = None,
    bank_id: str | None = None,
) -> list[dict[str, Any]]:
    """Replace everything older than the last ``keep`` messages with one LLM summary.

    Raises are caught and fall back to a naive truncation-summary so the
    caller never blows up on a transient LLM error.
    """
    if len(messages) <= keep:
        return messages

    old_messages = messages[:-keep]
    recent_messages = messages[-keep:]

    # exec-context §6.3: notify MemPalace / Hindsight BEFORE discarding.
    # Bounded wait (500ms default) — archive miss is logged, compression
    # continues. We do NOT block the LLM turn on a slow archive.
    await notify_pre_compression(old_messages, user_id=user_id, bank_id=bank_id)

    conv_parts: list[str] = []
    for msg in old_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str) and content.strip():
            conv_parts.append(f"[{role}]: {content[:200]}")

    if not conv_parts:
        return recent_messages

    conversation_text = "\n".join(conv_parts)

    try:
        from agent.llm_helper import llm_call

        summary = await llm_call(
            SUMMARY_PROMPT.format(conversation=conversation_text[:4000]),
            max_tokens=512,
        )
        if not summary:
            summary = "Previous conversation context."
    except Exception as exc:  # noqa: BLE001
        logger.warning("compression: LLM summary failed, falling back: %s", exc)
        summary = "Previous conversation: " + conversation_text[:500]

    summary_message = {
        "role": "user",
        "content": f"[Context Summary of {len(old_messages)} earlier messages]:\n{summary}",
    }
    return [summary_message, *recent_messages]


async def compress(
    messages: list[dict[str, Any]],
    *,
    keep: int = KEEP_MESSAGES,
    user_id: str | None = None,
    bank_id: str | None = None,
) -> list[dict[str, Any]]:
    """Top-level compression entry point. Alias for :func:`summarize_old_messages`."""
    return await summarize_old_messages(
        messages, keep=keep, user_id=user_id, bank_id=bank_id,
    )
