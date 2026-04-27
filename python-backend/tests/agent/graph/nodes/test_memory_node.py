from __future__ import annotations

import asyncio
from types import SimpleNamespace

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


@pytest.mark.asyncio
async def test_retain_conversation_writes_verbatim_and_queues_summary(monkeypatch):
    audit_events: list[dict] = []
    retain_calls: list[dict] = []
    queued: list[object] = []

    class _Engine:
        async def retain_batch_async(self, **kwargs):
            retain_calls.append(kwargs)
            assert kwargs["route"] == "verbatim"
            return [["verbatim-1"]]

        async def submit_async_retain(self, *_args, **_kwargs):
            raise AssertionError("summary retain must be queued, not awaited inline")

    class _Coherence:
        async def write_ahead(self, *_args, **_kwargs):
            return None

        async def detect_conflicts(self, *_args, **_kwargs):
            return SimpleNamespace(has_conflict=False, entries=[])

    async def _fake_audit_log(**kwargs):
        audit_events.append(kwargs)

    def _create_task(coro):
        queued.append(coro)
        coro.close()
        return None

    monkeypatch.setattr("memory_fusion.coherence.get_coherence_manager", lambda: _Coherence())
    monkeypatch.setattr("memory_fusion.engine.get_bank_id", lambda user_id: f"user_{user_id}")
    monkeypatch.setattr("agent.audit.logger.audit_log", _fake_audit_log)
    monkeypatch.setattr(memory_node.asyncio, "create_task", _create_task)

    await memory_node._retain_conversation_memory(
        state={
            "thread_id": "t1",
            "user_id": "u1",
            "agent_id": "a1",
            "agent_class": "advisory",
        },
        engine=_Engine(),
        role="default",
        user_msg="remember exact tool output",
        response="done",
    )

    assert retain_calls
    assert retain_calls[0]["contents"][0]["metadata"]["source"] == "automatic_memory_retain"
    assert len(queued) == 1
    assert audit_events[0]["metadata"]["route"] == "verbatim"
    assert audit_events[0]["metadata"]["providers"] == "verbatim,summary_async"
    assert audit_events[0]["metadata"]["summary_status"] == "background_queued"
