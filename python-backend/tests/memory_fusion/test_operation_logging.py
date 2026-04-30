from __future__ import annotations

import pytest

from agent.audit.logger import AuditAction
from memory_fusion.operation_logging import MemoryOperationContext, log_memory_operation


@pytest.mark.asyncio
async def test_log_memory_operation_adds_trace_metadata(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_audit_log(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("memory_fusion.operation_logging.audit_log", fake_audit_log)

    await log_memory_operation(
        action=AuditAction.MEMORY_RECALL,
        bank_id="user_1",
        route="fusion",
        operation_context=MemoryOperationContext(
            consumer="llm_agent",
            agent_id="agent-1",
            session_id="session-1",
            thread_id="thread-1",
            user_id="user-1",
            actor_role="agent",
        ),
        started_at=0.0,
        success=True,
        item_count=1,
        metadata={"source_ref": "session-001.jsonl#0"},
    )

    metadata = captured["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["source_status"] == "durable"
    assert metadata["raw_evidence_ref"] == "session-001.jsonl#0"
    assert metadata["operation_log_id"].startswith("memory-op:recall:user_1:fusion:session-001.jsonl")
    assert metadata["diff_ref"].startswith("memory-diff:user_1:fusion:session-001.jsonl")
