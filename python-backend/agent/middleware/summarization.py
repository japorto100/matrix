"""Context Summarization Middleware (exec-10 Phase 5.5).

Wenn das Context-Window sich dem Limit naehert, werden aeltere Messages
zusammengefasst. Die letzten N Messages bleiben vollstaendig erhalten.

3-Stufen Kompression (SOTA "Deep Agents" Pattern):
1. Offload: Grosse Tool-Results → gekuerzter Placeholder
2. Summarize: Aeltere Messages → LLM-generierte Zusammenfassung
3. Truncate: Falls immer noch zu gross → aelteste Messages entfernen

Konfiguration via ENV:
  AGENT_SUMMARIZE_THRESHOLD=0.7     # 70% des Context-Windows
  AGENT_SUMMARIZE_KEEP_MESSAGES=20  # Letzte 20 Messages behalten
  AGENT_SUMMARIZE_MODEL=claude-haiku-4-5  # Schnelles Model fuer Summaries
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Defaults
THRESHOLD_FRACTION = float(os.environ.get("AGENT_SUMMARIZE_THRESHOLD", "0.7"))
KEEP_MESSAGES = int(os.environ.get("AGENT_SUMMARIZE_KEEP_MESSAGES", "20"))
SUMMARIZE_MODEL = os.environ.get("AGENT_SUMMARIZE_MODEL", "claude-haiku-4-5")
TOOL_RESULT_MAX_CHARS = int(os.environ.get("AGENT_TOOL_RESULT_MAX_CHARS", "2000"))

# Token estimates (rough, fuer Threshold-Check)
MODEL_MAX_TOKENS: dict[str, int] = {
    "claude-sonnet-4-6": 200_000,
    "claude-opus-4-6": 200_000,
    "claude-haiku-4-5": 200_000,
    "gpt-4o": 128_000,
}
DEFAULT_MAX_TOKENS = 200_000
CHARS_PER_TOKEN = 4  # Rough estimate

SUMMARY_PROMPT = """Summarize the following conversation history concisely.
Preserve: key decisions, tool results, important facts, user preferences.
Discard: greetings, repeated questions, verbose tool outputs.
Output a single paragraph summary.

Conversation:
{conversation}"""


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Grobe Token-Schaetzung basierend auf Zeichenlaenge."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total_chars += len(json.dumps(block, default=str))
                else:
                    total_chars += len(str(block))
        else:
            total_chars += len(str(content))
    return total_chars // CHARS_PER_TOKEN


def offload_large_tool_results(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stufe 1: Grosse Tool-Results durch Kurzfassung ersetzen.

    Tool-Results ueber TOOL_RESULT_MAX_CHARS werden auf die ersten N Zeichen gekuerzt
    mit einem "[truncated]" Marker.
    """
    result = []
    for msg in messages:
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > TOOL_RESULT_MAX_CHARS:
                truncated = content[:TOOL_RESULT_MAX_CHARS] + "\n[... truncated, full result was {}chars]".format(len(content))
                result.append({**msg, "content": truncated})
                continue
        result.append(msg)
    return result


async def summarize_old_messages(
    messages: list[dict[str, Any]],
    keep: int = KEEP_MESSAGES,
) -> list[dict[str, Any]]:
    """Stufe 2: Aeltere Messages durch LLM-Summary ersetzen.

    Die letzten `keep` Messages bleiben vollstaendig.
    Alles davor wird zu einer einzelnen Summary-Message zusammengefasst.
    """
    if len(messages) <= keep:
        return messages

    old_messages = messages[:-keep]
    recent_messages = messages[-keep:]

    # Conversation-Text aus alten Messages extrahieren
    conv_parts = []
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
    except Exception as e:
        logger.warning("Summarization failed, using truncation fallback: %s", e)
        summary = "Previous conversation: " + conversation_text[:500]

    summary_message = {
        "role": "user",
        "content": f"[Context Summary of {len(old_messages)} earlier messages]:\n{summary}",
    }

    return [summary_message] + recent_messages


def should_summarize(messages: list[dict[str, Any]], model: str = "") -> bool:
    """Prueft ob Summarization noetig ist basierend auf Token-Threshold."""
    max_tokens = MODEL_MAX_TOKENS.get(model, DEFAULT_MAX_TOKENS)
    threshold = int(max_tokens * THRESHOLD_FRACTION)
    current = estimate_tokens(messages)
    return current > threshold


async def apply_context_management(
    messages: list[dict[str, Any]],
    model: str = "",
) -> list[dict[str, Any]]:
    """Vollstaendige Context-Management Pipeline.

    Stufe 1: Offload grosse Tool-Results
    Stufe 2: Summarize alte Messages (wenn noetig)
    Stufe 3: Truncate (falls immer noch zu gross)
    """
    # Stufe 1: Offload
    messages = offload_large_tool_results(messages)

    # Stufe 2: Summarize (wenn Threshold ueberschritten)
    if should_summarize(messages, model):
        logger.info("Context threshold reached, summarizing %d messages", len(messages))
        messages = await summarize_old_messages(messages)

    # Stufe 3: Hard Truncate (Fallback)
    max_tokens = MODEL_MAX_TOKENS.get(model, DEFAULT_MAX_TOKENS)
    while estimate_tokens(messages) > max_tokens * 0.9 and len(messages) > 2:
        messages = messages[1:]  # Aelteste Message entfernen

    return messages
