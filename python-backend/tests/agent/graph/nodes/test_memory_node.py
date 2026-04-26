from __future__ import annotations

import asyncio

import pytest

from agent.graph.nodes import memory_node


@pytest.mark.asyncio
async def test_memory_retain_node_times_out_without_blocking_turn(monkeypatch):
    audit_events: list[dict] = []

    async def _fake_get_memory_engine():
        return object()

    async def _fake_audit_log(**kwargs):
        audit_events.append(kwargs)

    async def _slow_retain(**_kwargs):
        await asyncio.sleep(10)

    monkeypatch.setattr(memory_node, "_memory_retain_timeout_seconds", lambda: 0.01)
    monkeypatch.setattr(memory_node, "_retain_conversation_memory", _slow_retain)
    monkeypatch.setattr(
        "memory_fusion.engine.get_memory_engine",
        _fake_get_memory_engine,
    )
    monkeypatch.setattr(
        "memory_fusion.engine.get_bank_id",
        lambda user_id: f"user_{user_id}",
    )
    monkeypatch.setattr("agent.audit.logger.audit_log", _fake_audit_log)

    result = await memory_node.memory_retain_node(
        {
            "thread_id": "t1",
            "user_id": "u1",
            "current_role": "default",
            "messages": [{"role": "user", "content": "remember slow retain"}],
            "final_response": "done",
            "agent_class": "advisory",
        }
    )

    assert result == {}
    assert audit_events
    assert audit_events[0]["success"] is False
    assert "timed out" in audit_events[0]["error"]
