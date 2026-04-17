"""Audit-oriented logging helpers for memory_fusion operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent.audit.logger import AuditAction, audit_duration, audit_log, audit_timer


@dataclass(frozen=True)
class MemoryOperationContext:
    consumer: str
    agent_id: str
    session_id: str
    thread_id: str
    user_id: str
    actor_role: str


def start_memory_timer() -> float:
    return audit_timer()


def extract_operation_context(
    *,
    consumer: str | None = None,
    request_context: Any = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryOperationContext:
    merged = dict(metadata or {})
    if isinstance(request_context, dict):
        merged = {**request_context, **merged}
    elif request_context is not None:
        for key in ("consumer", "agent_id", "session_id", "thread_id", "user_id", "actor_role"):
            value = getattr(request_context, key, None)
            if value not in (None, ""):
                merged.setdefault(key, value)
    return MemoryOperationContext(
        consumer=str(consumer or merged.get("consumer") or "agent_writer"),
        agent_id=str(merged.get("agent_id") or "memory_fusion"),
        session_id=str(merged.get("session_id") or ""),
        thread_id=str(merged.get("thread_id") or ""),
        user_id=str(merged.get("user_id") or ""),
        actor_role=str(merged.get("actor_role") or ""),
    )


async def log_memory_operation(
    *,
    action: AuditAction,
    bank_id: str,
    route: str,
    operation_context: MemoryOperationContext,
    started_at: float,
    success: bool,
    item_count: int = 0,
    query: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    payload = {
        "bank_id": bank_id,
        "route": route,
        "consumer": operation_context.consumer,
        "user_id": operation_context.user_id,
        "actor_role": operation_context.actor_role,
        "item_count": int(item_count),
        **dict(metadata or {}),
    }
    if query:
        payload["query"] = query[:300]
    await audit_log(
        action=action,
        agent_id=operation_context.agent_id or "memory_fusion",
        session_id=operation_context.session_id,
        thread_id=operation_context.thread_id,
        success=success,
        duration_ms=audit_duration(started_at),
        metadata=payload,
    )
