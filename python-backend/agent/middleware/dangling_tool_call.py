"""Dangling Tool Call Middleware (exec-10 Phase 5.1).

Wenn eine Agent-Session unterbrochen wird (User cancel, Timeout),
bleiben Tool-Calls ohne Response zurueck. Das LLM erwartet aber
fuer jeden tool_use Block ein entsprechendes tool_result.

Diese Middleware injiziert Placeholder-ToolMessages fuer verwaiste Tool-Calls.
Pattern uebernommen von deer-flow DanglingToolCallMiddleware.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def patch_dangling_tool_calls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Injiziert Placeholder-ToolMessages fuer Tool-Calls ohne Response.

    Scannt alle Messages: Fuer jeden tool_use Block in einer assistant-Message
    muss es eine nachfolgende tool-Message mit passender tool_use_id geben.
    Falls nicht → Placeholder einfuegen.

    Returns:
        Gepatchte Messages-Liste (oder unver. wenn kein Patching noetig).
    """
    # Sammle alle existierenden Tool-Result IDs
    existing_ids: set[str] = set()
    for msg in messages:
        if msg.get("role") == "tool":
            tid = msg.get("tool_use_id") or msg.get("tool_call_id")
            if tid:
                existing_ids.add(tid)

    # Pruefe ob Patching noetig
    needs_patch = False
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    if block.get("id") and block["id"] not in existing_ids:
                        needs_patch = True
                        break

    if not needs_patch:
        return messages

    # Patchen: Placeholder nach jeder assistant-Message mit verwaisten Tool-Calls
    patched: list[dict[str, Any]] = []
    patched_ids: set[str] = set()

    for msg in messages:
        patched.append(msg)

        if msg.get("role") != "assistant":
            continue

        content = msg.get("content")
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tc_id = block.get("id")
            if tc_id and tc_id not in existing_ids and tc_id not in patched_ids:
                patched.append({
                    "role": "tool",
                    "tool_use_id": tc_id,
                    "content": "[Tool call was interrupted and did not return a result.]",
                })
                patched_ids.add(tc_id)
                logger.debug("Patched dangling tool call: %s", tc_id)

    if patched_ids:
        logger.info("Patched %d dangling tool call(s)", len(patched_ids))

    return patched
