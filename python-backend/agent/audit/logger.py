# Audit Logger — exec-12 Phase 2.1
# Structured JSON Lines audit trail for agent actions.
# Append-only, async, pluggable storage backend.

from __future__ import annotations

import time
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from agent.audit.store import get_audit_store


class AuditAction(StrEnum):
    # LLM_REQUEST removed per ADR-002 — redundant with OTel span for the
    # request side. LLM_RESPONSE is the only audit-side LLM event now.
    LLM_RESPONSE = "llm_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    # Legacy APPROVAL_* removed — replaced by CONSENT_REQUEST/CONSENT_DECISION
    MEMORY_RECALL = "memory_recall"
    MEMORY_RETAIN = "memory_retain"
    MEMORY_LIST = "memory_list"
    MEMORY_GET = "memory_get"
    MEMORY_DELETE = "memory_delete"
    SANDBOX_EXEC = "sandbox_exec"
    CONSENT_REQUEST = "consent_request"
    CONSENT_DECISION = "consent_decision"
    RATE_LIMIT_HIT = "rate_limit_hit"
    SKILL_FOUND = "skill_found"
    SKILL_REFINED = "skill_refined"
    SKILL_USED = "skill_used"


async def audit_log(
    *,
    action: AuditAction,
    agent_id: str = "default",
    session_id: str = "",
    thread_id: str = "",
    tool_name: str | None = None,
    input_data: Any = None,
    output_data: Any = None,
    duration_ms: float | None = None,
    success: bool = True,
    iteration: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emit a structured audit event. Fire-and-forget, never raises."""
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action.value,
        "agentId": agent_id,
        "sessionId": session_id,
        "threadId": thread_id,
        "success": success,
    }
    if tool_name is not None:
        entry["toolName"] = tool_name
    if input_data is not None:
        entry["input"] = _safe_truncate(input_data)
    if output_data is not None:
        entry["output"] = _safe_truncate(output_data)
    if duration_ms is not None:
        entry["duration_ms"] = round(duration_ms, 2)
    if iteration is not None:
        entry["iteration"] = iteration
    if metadata:
        entry["metadata"] = metadata

    store = get_audit_store()
    await store.append(entry)


def audit_timer() -> float:
    """Return a monotonic start time. Use with audit_duration()."""
    return time.perf_counter()


def audit_duration(start: float) -> float:
    """Return elapsed ms since start."""
    return (time.perf_counter() - start) * 1000


def _safe_truncate(data: Any, max_len: int = 2000) -> Any:
    """Truncate large payloads to keep audit logs manageable."""
    if isinstance(data, str) and len(data) > max_len:
        return data[:max_len] + f"... [truncated, {len(data)} chars]"
    if isinstance(data, dict):
        serialized = str(data)
        if len(serialized) > max_len:
            return {"_truncated": True, "_preview": serialized[:max_len]}
    return data
