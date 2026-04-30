from __future__ import annotations

from agent.runtime_events import make_runtime_event, redact_runtime_payload


def test_runtime_event_redacts_secret_metadata() -> None:
    event = make_runtime_event(
        kind="tool",
        status="completed",
        name="memory_search",
        thread_id="thread-1",
        turn=2,
        metadata={
            "api_key": "sk-secret",
            "nested": {"authorization": "Bearer token", "safe": "ok"},
        },
        payload={"token": "raw-token", "tail": "ok"},
    )

    assert event["contract"] == "agent-runtime-event/v1"
    assert event["run_id"] == "thread-1"
    assert event["session_id"] == "thread-1"
    assert event["thread_id"] == "thread-1"
    assert event["turn_id"] == "thread-1:turn:2"
    assert event["span_id"] == event["event_id"]
    assert event["metadata"]["api_key"] == "[redacted]"
    assert event["metadata"]["nested"]["authorization"] == "[redacted]"
    assert event["metadata"]["nested"]["safe"] == "ok"
    assert event["payload"]["token"] == "[redacted]"
    assert event["payload"]["tail"] == "ok"
    assert event["redaction"]["policy"] == "runtime-event-redaction/v1"
    assert event["redaction"]["applied"] is True


def test_runtime_event_preserves_explicit_identity_fields() -> None:
    event = make_runtime_event(
        kind="subagent",
        status="started",
        name="subagent.delegation.started",
        event_id="evt-child-start",
        run_id="run-1",
        session_id="session-1",
        thread_id="thread-parent",
        span_id="span-child",
        parent_event_id="evt-parent",
        turn_id="turn-1",
    )

    assert event["run_id"] == "run-1"
    assert event["session_id"] == "session-1"
    assert event["thread_id"] == "thread-parent"
    assert event["span_id"] == "span-child"
    assert event["parent_id"] == "evt-parent"
    assert event["parent_event_id"] == "evt-parent"
    assert event["turn_id"] == "turn-1"


def test_redact_runtime_payload_truncates_large_text() -> None:
    payload = redact_runtime_payload({"text": "x" * 900})

    assert payload["text"].endswith("...[truncated]")
    assert len(payload["text"]) < 840
