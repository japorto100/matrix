from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.audit.logger import AuditAction
from agent.tools.memory_hindsight import MemoryAddTool, MemorySearchTool


@pytest.mark.asyncio
async def test_memory_search_tool_emits_memory_recall_audit(monkeypatch):
    audit_events = []

    async def _audit_log(**kwargs):
        audit_events.append(kwargs)

    class _Engine:
        async def recall_async(self, **kwargs):
            assert kwargs["fact_type"] == ["experience"]
            return SimpleNamespace(
                results=[
                    SimpleNamespace(
                        text="user prefers swing trading",
                        fact_type="experience",
                        entities=["user"],
                    )
                ]
            )

    async def _get_memory_engine():
        return _Engine()

    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("memory_fusion.engine.get_memory_engine", _get_memory_engine)
    monkeypatch.setattr("memory_fusion.engine.get_bank_id", lambda user_id: "user-u1")

    result = await MemorySearchTool().execute(
        {"query": "risk preference", "fact_type": "experience"},
        SimpleNamespace(user_id="u1", thread_id="t1"),
    )

    assert result["count"] == 1
    assert audit_events[0]["action"] == AuditAction.MEMORY_RECALL
    assert audit_events[0]["thread_id"] == "t1"
    assert audit_events[0]["metadata"]["route"] == "fusion"
    assert audit_events[0]["metadata"]["source"] == "explicit_memory_tool"


@pytest.mark.asyncio
async def test_memory_search_tool_omits_fact_filter_by_default(monkeypatch):
    class _Engine:
        async def recall_async(self, **kwargs):
            assert kwargs["fact_type"] is None
            return SimpleNamespace(results=[])

    async def _get_memory_engine():
        return _Engine()

    async def _audit_log(**_kwargs):
        return None

    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("memory_fusion.engine.get_memory_engine", _get_memory_engine)
    monkeypatch.setattr("memory_fusion.engine.get_bank_id", lambda user_id: "user-u1")

    result = await MemorySearchTool().execute(
        {"query": "risk preference"},
        SimpleNamespace(user_id="u1", thread_id="t1"),
    )

    assert result["count"] == 0


@pytest.mark.asyncio
async def test_memory_search_tool_omits_unknown_fact_filter(monkeypatch):
    audit_events = []

    async def _audit_log(**kwargs):
        audit_events.append(kwargs)

    class _Engine:
        async def recall_async(self, **kwargs):
            assert kwargs["fact_type"] is None
            return SimpleNamespace(results=[])

    async def _get_memory_engine():
        return _Engine()

    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("memory_fusion.engine.get_memory_engine", _get_memory_engine)
    monkeypatch.setattr("memory_fusion.engine.get_bank_id", lambda user_id: "user-u1")

    result = await MemorySearchTool().execute(
        {"query": "probe", "fact_type": "made_up_type"},
        SimpleNamespace(user_id="u1", thread_id="t1"),
    )

    assert result["count"] == 0
    assert audit_events[0]["metadata"]["fact_type"] == ""
    assert audit_events[0]["metadata"]["original_fact_type"] == "made_up_type"


@pytest.mark.asyncio
async def test_memory_add_tool_emits_memory_retain_audit(monkeypatch):
    audit_events = []

    async def _audit_log(**kwargs):
        audit_events.append(kwargs)

    class _Engine:
        async def retain_batch_async(self, **kwargs):
            return [["fact-1", "fact-2"]]

    async def _get_memory_engine():
        return _Engine()

    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("memory_fusion.engine.get_memory_engine", _get_memory_engine)
    monkeypatch.setattr("memory_fusion.engine.get_bank_id", lambda user_id: "user-u1")

    result = await MemoryAddTool().execute(
        {"content": "User risks 1% per trade", "fact_type": "experience"},
        SimpleNamespace(user_id="u1", thread_id="t1", agent_class="advisory"),
    )

    assert result == {"stored": True, "facts_extracted": 2}
    assert audit_events[0]["action"] == AuditAction.MEMORY_RETAIN
    assert audit_events[0]["thread_id"] == "t1"
    assert audit_events[0]["metadata"]["item_count"] == 2
    assert audit_events[0]["metadata"]["route"] == "fusion"
    assert audit_events[0]["metadata"]["source"] == "explicit_memory_tool"


@pytest.mark.asyncio
async def test_memory_add_tool_maps_world_to_experience(monkeypatch):
    calls = []

    async def _audit_log(**kwargs):
        calls.append(("audit", kwargs))

    class _Engine:
        async def retain_batch_async(self, **kwargs):
            calls.append(("retain", kwargs))
            return [["fact-1"]]

    async def _get_memory_engine():
        return _Engine()

    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("memory_fusion.engine.get_memory_engine", _get_memory_engine)
    monkeypatch.setattr("memory_fusion.engine.get_bank_id", lambda user_id: "user-u1")

    result = await MemoryAddTool().execute(
        {"content": "remember this", "fact_type": "world"},
        SimpleNamespace(user_id="u1", thread_id="t1", agent_class="advisory"),
    )

    assert result["stored"] is True
    retain_call = next(kwargs for kind, kwargs in calls if kind == "retain")
    item = retain_call["contents"][0]
    assert item["fact_type"] == "experience"
    assert item["metadata"]["original_fact_type"] == "world"
    audit_call = next(kwargs for kind, kwargs in calls if kind == "audit")
    assert audit_call["metadata"]["fact_type"] == "experience"
    assert audit_call["metadata"]["original_fact_type"] == "world"


@pytest.mark.asyncio
async def test_memory_add_tool_maps_unknown_fact_type_to_experience(monkeypatch):
    calls = []

    async def _audit_log(**kwargs):
        calls.append(("audit", kwargs))

    class _Engine:
        async def retain_batch_async(self, **kwargs):
            calls.append(("retain", kwargs))
            return [["fact-1"]]

    async def _get_memory_engine():
        return _Engine()

    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("memory_fusion.engine.get_memory_engine", _get_memory_engine)
    monkeypatch.setattr("memory_fusion.engine.get_bank_id", lambda user_id: "user-u1")

    result = await MemoryAddTool().execute(
        {"content": "remember this", "fact_type": "project_memory"},
        SimpleNamespace(user_id="u1", thread_id="t1", agent_class="advisory"),
    )

    assert result["stored"] is True
    retain_call = next(kwargs for kind, kwargs in calls if kind == "retain")
    assert retain_call["contents"][0]["fact_type"] == "experience"
    assert retain_call["contents"][0]["metadata"]["original_fact_type"] == "project_memory"


@pytest.mark.asyncio
async def test_memory_add_tool_dispatches_summary_in_background(monkeypatch):
    created = []

    async def _audit_log(**_kwargs):
        return None

    def _create_task(coro):
        created.append(coro)
        coro.close()
        return None

    class _Engine:
        async def retain_batch_async(self, **_kwargs):
            return [["fact-1"]]

        async def submit_async_retain(self, **_kwargs):
            raise AssertionError("summary retain must not be awaited inline")

    async def _get_memory_engine():
        return _Engine()

    monkeypatch.setattr("agent.tools.memory_hindsight.asyncio.create_task", _create_task)
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)
    monkeypatch.setattr("memory_fusion.engine.get_memory_engine", _get_memory_engine)
    monkeypatch.setattr("memory_fusion.engine.get_bank_id", lambda user_id: "user-u1")

    result = await MemoryAddTool().execute(
        {"content": "remember this"},
        SimpleNamespace(user_id="u1", thread_id="t1", agent_class="advisory"),
    )

    assert result["stored"] is True
    assert len(created) == 1
