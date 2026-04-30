from __future__ import annotations

from agent.a2a.client import A2ATask
from agent.graph.nodes import a2a_node


def _state() -> dict:
    return {
        "current_role": "researcher",
        "messages": [{"role": "user", "content": "analyze AAPL"}],
        "thread_id": "thread-parent",
    }


async def test_a2a_delegate_node_fails_closed_when_spawn_depth_default_zero(
    monkeypatch,
) -> None:
    calls = {"client": 0}
    monkeypatch.setenv("AGENT_REMOTE_RESEARCHER", "http://agent.local")
    monkeypatch.delenv("AGENT_A2A_MAX_SPAWN_DEPTH", raising=False)
    monkeypatch.setattr(a2a_node, "REMOTE_AGENTS", {})

    class FakeClient:
        def __init__(self) -> None:
            calls["client"] += 1

    monkeypatch.setattr(a2a_node, "A2AClient", FakeClient)

    result = await a2a_node.a2a_delegate_node(_state())  # type: ignore[arg-type]

    assert result == {}
    assert calls["client"] == 0


async def test_a2a_delegate_node_uses_fresh_bounded_child_context(
    monkeypatch,
) -> None:
    captured: dict = {}
    monkeypatch.setenv("AGENT_REMOTE_RESEARCHER", "http://agent.local")
    monkeypatch.setenv("AGENT_A2A_MAX_SPAWN_DEPTH", "1")
    monkeypatch.setattr(a2a_node, "REMOTE_AGENTS", {})

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
        "memory_scope:explicit_context_only"
    )
    assert captured["closed"] is True
