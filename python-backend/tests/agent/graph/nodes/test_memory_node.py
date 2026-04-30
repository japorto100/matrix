from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from agent.graph.nodes import memory_node


@pytest.mark.asyncio
async def test_memory_recall_node_emits_unavailable_runtime_event(monkeypatch):
    async def _fake_get_memory_engine():
        return None

    monkeypatch.setattr(
        "memory_fusion.engine.get_memory_engine",
        _fake_get_memory_engine,
    )

    result = await memory_node.memory_recall_node(
        {
            "thread_id": "t1",
            "user_id": "u1",
            "current_role": "default",
            "messages": [{"role": "user", "content": "recall my preference"}],
        }
    )

    event = result["runtime_events"][0]
    assert event["kind"] == "memory"
    assert event["status"] == "blocked"
    assert event["name"] == "memory.recall.unavailable"


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

    assert result["degradation_flags"] == ["memory_retain_timeout"]
    assert result["runtime_events"][0]["kind"] == "memory"
    assert result["runtime_events"][0]["status"] == "stale"
    assert result["runtime_events"][0]["name"] == "memory.retain.timeout"
    assert audit_events
    assert audit_events[0]["success"] is False
    assert "timed out" in audit_events[0]["metadata"]["error"]
    assert audit_events[0]["metadata"]["runtime_events"][0]["name"] == "memory.retain.timeout"


@pytest.mark.asyncio
async def test_memory_recall_node_surfaces_source_session_refs(monkeypatch):
    audit_events: list[dict] = []

    class _Engine:
        def _normalize_query(self, query: str) -> str:
            return query

        async def recall_async(self, **kwargs):
            assert kwargs["operation_context"]["thread_id"] == "thread-1"
            return SimpleNamespace(
                results=[
                    SimpleNamespace(
                        id="mem-1",
                        text="The portfolio risk budget is capped at two percent.",
                        fact_type="experience",
                        entities=["portfolio"],
                        tags=["risk"],
                        document_id="session-001.jsonl",
                        chunk_id="0",
                        metadata={
                            "memory_layer": "personal_raw",
                            "source_ref": "session-001.jsonl#0",
                            "raw_evidence_ref": "session-001.jsonl#0",
                            "operation_log_id": "memory-op:recall:user_1:fusion:session-001.jsonl",
                            "diff_ref": "memory-diff:user_1:fusion:session-001.jsonl",
                            "thread_id": "thread-1",
                            "session_id": "session-1",
                            "room_id": "!room:matrix.local",
                            "status": "available",
                        },
                    )
                ],
                entities={},
            )

    async def _fake_get_memory_engine():
        return _Engine()

    async def _fake_audit_log(**kwargs):
        audit_events.append(kwargs)

    memory_node._injected_context.clear()
    monkeypatch.setattr(
        "memory_fusion.engine.get_memory_engine",
        _fake_get_memory_engine,
    )
    monkeypatch.setattr(
        "memory_fusion.engine.get_bank_id",
        lambda user_id: f"user_{user_id}",
    )
    monkeypatch.setattr("agent.audit.logger.audit_log", _fake_audit_log)

    result = await memory_node.memory_recall_node(
        {
            "thread_id": "thread-1",
            "user_id": "u1",
            "current_role": "default",
            "messages": [{"role": "user", "content": "recall risk budget"}],
            "iteration": 2,
        }
    )

    block = result["context_blocks"][0]
    assert block["sourceRefs"] == ["session-001.jsonl#0"]
    assert block["rawEvidenceRef"] == "session-001.jsonl#0"
    assert block["threadId"] == "thread-1"
    assert block["sessionId"] == "session-1"
    assert block["roomId"] == "!room:matrix.local"

    event = result["runtime_events"][0]
    context_ref = event["metadata"]["context_refs"][0]
    assert event["name"] == "memory.recall.completed"
    assert context_ref["source_refs"] == ["session-001.jsonl#0"]
    assert context_ref["raw_evidence_ref"] == "session-001.jsonl#0"
    assert context_ref["thread_id"] == "thread-1"
    assert context_ref["session_id"] == "session-1"
    assert context_ref["room_id"] == "!room:matrix.local"
    assert "portfolio risk budget" not in str(context_ref)
    assert audit_events[0]["metadata"]["runtime_events"][0]["metadata"]["context_refs"]


@pytest.mark.asyncio
async def test_memory_retain_node_blocks_child_shared_memory_writes(monkeypatch):
    async def _fail_get_memory_engine():
        raise AssertionError("child memory-write block must happen before engine lookup")

    monkeypatch.setattr(
        "memory_fusion.engine.get_memory_engine",
        _fail_get_memory_engine,
    )

    result = await memory_node.memory_retain_node(
        {
            "thread_id": "a2a-child-1",
            "user_id": "u1",
            "current_role": "default",
            "messages": [{"role": "user", "content": "remember child output"}],
            "final_response": "done",
            "agent_class": "advisory",
            "memory_write_policy": "parent_only",
            "child_memory_write_allowed": False,
            "parent_thread_id": "parent-1",
            "spawn_depth": 1,
        }
    )

    event = result["runtime_events"][0]
    assert event["kind"] == "memory"
    assert event["status"] == "blocked"
    assert event["name"] == "memory.retain.blocked"
    assert event["metadata"]["reason"] == "child_memory_write_disabled"
    assert event["metadata"]["memory_write_policy"] == "parent_only"
    assert event["metadata"]["parent_thread_id"] == "parent-1"


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

    metadata = await memory_node._retain_conversation_memory(
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
    assert audit_events[0]["metadata"]["runtime_events"][0]["name"] == "memory.retain.completed"
    assert metadata["route"] == "verbatim"
    assert metadata["summary_status"] == "background_queued"


@pytest.mark.asyncio
async def test_memory_retain_node_emits_completed_runtime_event(monkeypatch):
    async def _fake_get_memory_engine():
        return object()

    async def _fake_retain(**_kwargs):
        return {
            "bank_id": "user_u1",
            "role": "default",
            "route": "verbatim",
            "provider": "fusion",
            "summary_status": "background_queued",
        }

    monkeypatch.setattr(memory_node, "_retain_conversation_memory", _fake_retain)
    monkeypatch.setattr(
        "memory_fusion.engine.get_memory_engine",
        _fake_get_memory_engine,
    )

    result = await memory_node.memory_retain_node(
        {
            "thread_id": "t1",
            "user_id": "u1",
            "current_role": "default",
            "messages": [{"role": "user", "content": "remember this"}],
            "final_response": "done",
            "agent_class": "advisory",
        }
    )

    event = result["runtime_events"][0]
    assert event["kind"] == "memory"
    assert event["status"] == "completed"
    assert event["name"] == "memory.retain.completed"
    assert event["metadata"]["route"] == "verbatim"
