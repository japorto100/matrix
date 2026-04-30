from __future__ import annotations

from types import SimpleNamespace

from agent.control import sessions


async def _noop_audit(**_kwargs) -> None:
    return None


async def test_pause_session_returns_explicit_unsupported_runtime_event(monkeypatch) -> None:
    monkeypatch.setattr(sessions, "_audit_session_control", _noop_audit)

    payload = await sessions.pause_session(
        "thread-1",
        sessions.SessionControlRequest(reason="operator test"),
        SimpleNamespace(headers={"x-auth-user": "alice"}),
    )

    assert payload["status"] == "unsupported"
    event = payload["runtime_events"][0]
    assert event["kind"] == "control"
    assert event["status"] == "blocked"
    assert event["name"] == "session.pause.unsupported"
    assert event["metadata"]["supported"] is False


async def test_kill_session_requires_confirm_before_deleting(monkeypatch) -> None:
    monkeypatch.setattr(sessions, "_audit_session_control", _noop_audit)

    payload = await sessions.kill_session_control(
        "thread-1",
        sessions.SessionControlRequest(confirm=False),
        SimpleNamespace(headers={"x-auth-user": "alice"}),
    )

    assert payload["status"] == "confirmation_required"
    event = payload["runtime_events"][0]
    assert event["status"] == "needs_approval"
    assert event["metadata"]["outcome"] == "confirmation_required"


async def test_kill_session_confirm_marks_killed_runtime_event(monkeypatch) -> None:
    monkeypatch.setattr(sessions, "_audit_session_control", _noop_audit)
    monkeypatch.setattr(
        sessions,
        "_kill_session_rows",
        lambda *_args, **_kwargs: {
            "deleted_checkpoints": 2,
            "updated_sessions": ["session-1"],
        },
    )

    payload = await sessions.kill_session_control(
        "thread-1",
        sessions.SessionControlRequest(confirm=True, reason="stale run"),
        SimpleNamespace(headers={"x-auth-user": "alice"}),
    )

    assert payload["status"] == "killed"
    assert payload["deleted_checkpoints"] == 2
    event = payload["runtime_events"][0]
    assert event["status"] == "cancelled"
    assert event["metadata"]["outcome"] == "killed"
    assert event["metadata"]["updated_sessions"] == ["session-1"]
