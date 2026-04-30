"""Context compaction — lossless-or-fast-lossless pruning (P5 split).

Compaction is the cheap, mechanical side of context-management: remove
redundancy without calling an LLM. Triggered by
:data:`context.context_engine.ContextStage.compaction` (~85% of context
window).

Operations here must be **deterministic** and **cheap** (no async LLM
calls, no DB reads). The expensive, lossy summarisation lives in
:mod:`agent.middleware.compression`.

Tactics currently implemented:

1. ``offload_large_tool_results`` — truncate tool-message content past
   :data:`TOOL_RESULT_MAX_CHARS` with a ``[truncated]`` marker.

Split rationale (exec-context §6.3):
* Compaction (mechanical) → safe to run per-turn; no data-loss guarantee
  needed because facts are recoverable from tool_call_ids.
* Compression (LLM summary) → lossy; requires ``pre_compression`` event
  contract so mempalace can verbatim-archive before we throw away context.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

TOOL_RESULT_MAX_CHARS = int(os.environ.get("AGENT_TOOL_RESULT_MAX_CHARS", "2000"))
CHARS_PER_TOKEN = 4  # rough heuristic shared across middleware modules


__all__ = [
    "TOOL_RESULT_MAX_CHARS",
    "CHARS_PER_TOKEN",
    "estimate_tokens",
    "offload_large_tool_results",
    "compact",
]


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough character-based token estimate.

    Shared across compaction/compression/runner so threshold logic is
    consistent. Uses 4 chars/token which is a defensible average across
    English, German, and JSON tool-output blocks.
    """
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


_TRUNCATION_MARKER = "[... truncated, full result was "


def _tool_result_ref(msg: dict[str, Any], *, content_hash: str) -> str:
    for key in ("tool_call_id", "id", "call_id", "toolUseId", "tool_use_id"):
        value = str(msg.get(key) or "").strip()
        if value:
            return f"tool:{value}"
    metadata = msg.get("metadata")
    if isinstance(metadata, dict):
        for key in ("source_ref", "raw_evidence_ref", "artifact_id"):
            value = str(metadata.get(key) or "").strip()
            if value:
                return value
    return f"tool-result:sha256:{content_hash[:16]}"


def offload_large_tool_results(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Truncate tool-message bodies past ``TOOL_RESULT_MAX_CHARS``.

    Preserves the first N chars plus a marker so the LLM knows the value
    was truncated (vs. missing entirely). Non-tool messages pass through.
    Idempotent — already-truncated content is recognised via the marker
    and left alone so re-running compaction can't double-truncate.
    """
    result: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if (
                isinstance(content, str)
                and len(content) > TOOL_RESULT_MAX_CHARS
                and _TRUNCATION_MARKER not in content
            ):
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                offload_ref = _tool_result_ref(msg, content_hash=content_hash)
                truncated = (
                    content[:TOOL_RESULT_MAX_CHARS]
                    + f"\n{_TRUNCATION_MARKER}{len(content)}chars, sha256:{content_hash[:12]}]"
                )
                metadata = dict(msg.get("metadata") or {})
                compaction_metadata = dict(metadata.get("compaction") or {})
                compaction_metadata.update(
                    {
                        "truncated": True,
                        "offload_ref": offload_ref,
                        "full_content_chars": len(content),
                        "content_sha256": content_hash,
                        "preview_chars": TOOL_RESULT_MAX_CHARS,
                    }
                )
                metadata["compaction"] = compaction_metadata
                result.append({**msg, "content": truncated, "metadata": metadata})
                continue
        result.append(msg)
    return result


def compact(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply all compaction passes. Idempotent — re-running is a no-op."""
    return offload_large_tool_results(messages)
