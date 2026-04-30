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
    )

    assert event["contract"] == "agent-runtime-event/v1"
    assert event["metadata"]["api_key"] == "[redacted]"
    assert event["metadata"]["nested"]["authorization"] == "[redacted]"
    assert event["metadata"]["nested"]["safe"] == "ok"


def test_redact_runtime_payload_truncates_large_text() -> None:
    payload = redact_runtime_payload({"text": "x" * 900})

    assert payload["text"].endswith("...[truncated]")
    assert len(payload["text"]) < 840
