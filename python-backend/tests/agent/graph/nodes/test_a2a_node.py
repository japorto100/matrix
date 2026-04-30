from __future__ import annotations

import asyncio

from agent.a2a.client import A2ATask
from agent.graph.nodes import a2a_node


def _state() -> dict:
    return {
        "current_role": "researcher",
        "messages": [{"role": "user", "content": "analyze AAPL"}],
        "thread_id": "thread-parent",
        "runner_variant": "langgraph",
        "tool_definitions": [
            {"name": "semantic_lookup"},
            {"name": "memory_add"},
            {"name": "delegate_task"},
        ],
    }


async def test_a2a_delegate_node_fails_closed_when_spawn_depth_default_zero(
    monkeypatch,
) -> None:
    calls = {"client": 0}
    audit_rows: list[dict] = []

    async def _audit_log(**kwargs):
        audit_rows.append(kwargs)

    monkeypatch.setenv("AGENT_REMOTE_RESEARCHER", "http://agent.local")
    monkeypatch.delenv("AGENT_A2A_MAX_SPAWN_DEPTH", raising=False)
    monkeypatch.setattr(a2a_node, "REMOTE_AGENTS", {})
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)

    class FakeClient:
        def __init__(self) -> None:
            calls["client"] += 1

    monkeypatch.setattr(a2a_node, "A2AClient", FakeClient)

    result = await a2a_node.a2a_delegate_node(_state())  # type: ignore[arg-type]

    assert result["degradation_flags"] == ["a2a_delegation_spawn_depth_blocked"]
    assert result["runtime_events"][0]["kind"] == "subagent"
    assert result["runtime_events"][0]["status"] == "blocked"
    assert result["runtime_events"][0]["metadata"]["delegation_decision"] == "blocked"
    assert audit_rows[0]["metadata"]["runtime_events"][0]["name"] == "subagent.delegation.blocked"
    assert calls["client"] == 0


async def test_a2a_delegate_node_uses_fresh_bounded_child_context(
    monkeypatch,
) -> None:
    captured: dict = {}
    audit_rows: list[dict] = []

    async def _audit_log(**kwargs):
        audit_rows.append(kwargs)

    monkeypatch.setenv("AGENT_REMOTE_RESEARCHER", "http://agent.local")
    monkeypatch.setenv("AGENT_A2A_MAX_SPAWN_DEPTH", "1")
    monkeypatch.setattr(a2a_node, "REMOTE_AGENTS", {})
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)

    class FakeClient:
        async def send_message(self, **kwargs):
            captured.update(kwargs)
            return A2ATask(task_id="task-1", state="completed", result="child result")

        async def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(a2a_node, "A2AClient", FakeClient)

    result = await a2a_node.a2a_delegate_node(_state())  # type: ignore[arg-type]

    assert result["done"] is True
    assert result["final_response"] == "child result"
    assert captured["agent_url"] == "http://agent.local"
    assert captured["message"] == "analyze AAPL"
    assert captured["context"] == (
        "Delegated from Matrix orchestrator; role:researcher; "
        "parent_thread_id:thread-parent; spawn_depth:1; max_spawn_depth:1; "
        "memory_scope:explicit_context_only; context_mode:isolated; "
        "allowed_tools:semantic_lookup; memory_write_policy:parent_only; "
        "approval_mode:non_interactive_auto_deny"
    )
    assert captured["closed"] is True
    event_names = [event["name"] for event in result["runtime_events"]]
    assert event_names == [
        "subagent.delegation.accepted",
        "subagent.delegation.started",
        "subagent.delegation.completed",
        "subagent.parent_memory_handoff",
    ]
    handoff = result["runtime_events"][-1]
    assert handoff["kind"] == "memory"
    assert handoff["metadata"]["child_memory_write_allowed"] is False
    assert handoff["metadata"]["result_digest"]
    assert audit_rows[0]["metadata"]["child_task_id"] == "task-1"
    assert audit_rows[0]["metadata"]["runtime_events"][2]["status"] == "completed"


async def test_a2a_delegate_node_surfaces_timeout_as_stale_runtime_event(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENT_REMOTE_RESEARCHER", "http://agent.local")
    monkeypatch.setenv("AGENT_A2A_MAX_SPAWN_DEPTH", "1")
    monkeypatch.setattr(a2a_node, "REMOTE_AGENTS", {})

    class FakeClient:
        async def send_message(self, **_kwargs):
            return A2ATask(task_id="task-timeout", state="timeout", error="timeout")

        async def close(self) -> None:
            pass

    monkeypatch.setattr(a2a_node, "A2AClient", FakeClient)

    result = await a2a_node.a2a_delegate_node(_state())  # type: ignore[arg-type]

    assert result["degradation_flags"] == ["a2a_delegation_timeout"]
    assert result["runtime_events"][-1]["status"] == "stale"
    assert result["runtime_events"][-1]["metadata"]["child_task_id"] == "task-timeout"


async def test_a2a_delegate_node_wraps_blocking_client_with_node_timeout(
    monkeypatch,
) -> None:
    audit_rows: list[dict] = []
    captured: dict = {}

    async def _audit_log(**kwargs):
        audit_rows.append(kwargs)

    monkeypatch.setenv("AGENT_REMOTE_RESEARCHER", "http://agent.local")
    monkeypatch.setenv("AGENT_A2A_MAX_SPAWN_DEPTH", "1")
    monkeypatch.setenv("AGENT_A2A_DELEGATION_TIMEOUT_SECONDS", "0.01")
    monkeypatch.setattr(a2a_node, "REMOTE_AGENTS", {})
    monkeypatch.setattr("agent.audit.logger.audit_log", _audit_log)

    class FakeClient:
        async def send_message(self, **_kwargs):
            await asyncio.sleep(60)
            return A2ATask(task_id="never", state="completed", result="late")

        async def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(a2a_node, "A2AClient", FakeClient)

    result = await a2a_node.a2a_delegate_node(_state())  # type: ignore[arg-type]

    assert result["degradation_flags"] == ["a2a_delegation_timeout"]
    assert result["runtime_events"][-1]["name"] == "subagent.delegation.timeout"
    assert result["runtime_events"][-1]["status"] == "stale"
    assert result["runtime_events"][-1]["metadata"]["error"] == "node_level_timeout"
    assert captured["closed"] is True
    assert audit_rows[0]["success"] is False
    assert audit_rows[0]["metadata"]["error"] == "node_level_timeout"
