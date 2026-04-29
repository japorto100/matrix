from __future__ import annotations

from agent.control.ops import (
    audit_event_to_ops_event,
    build_ops_read_model,
    redact_payload,
)


def _audit_event(**overrides):
    event = {
        "id": 1,
        "timestamp": "2026-04-29T12:00:00+00:00",
        "action": "tool_result",
        "user_id": "u1",
        "thread_id": "thread-1",
        "agent_role": "researcher",
        "tool_name": "sandbox_execute",
        "input": {"api_key": "secret", "query": "safe"},
        "output": {"token": "secret", "result": "ok"},
        "duration_ms": 12,
        "success": True,
        "error": "",
        "metadata": {"approval_ref": "approval-1"},
    }
    event.update(overrides)
    return event


def test_redact_payload_removes_nested_secrets():
    redacted = redact_payload(
        {
            "api_key": "sk-test",
            "nested": {"Authorization": "Bearer secret", "value": "ok"},
            "items": [{"password": "pw"}, {"safe": "yes"}],
        }
    )

    assert redacted["api_key"] == "[redacted]"
    assert redacted["nested"]["Authorization"] == "[redacted]"
    assert redacted["nested"]["value"] == "ok"
    assert redacted["items"][0]["password"] == "[redacted]"


def test_audit_event_to_ops_event_derives_type_risk_and_approval_ref():
    event = audit_event_to_ops_event(
        _audit_event(),
        {"risk": "high", "approval": "confirm", "group": "code_execution"},
    )

    assert event["event_type"] == "tool_call"
    assert event["status"] == "active"
    assert event["risk"] == "high"
    assert event["approval_ref"] == "approval-1"
    assert event["input"]["api_key"] == "[redacted]"
    assert event["output"]["token"] == "[redacted]"


def test_build_ops_read_model_filters_and_reports_blockers():
    model = build_ops_read_model(
        audit_events=[
            _audit_event(id=1, tool_name="sandbox_execute", success=False),
            _audit_event(id=2, tool_name="memory_search", action="memory_recall"),
        ],
        sessions=[
            {
                "thread_id": "thread-1",
                "role": "researcher",
                "checkpoint_count": 2,
                "is_active": False,
            }
        ],
        tool_risks={
            "sandbox_execute": {"risk": "high"},
            "memory_search": {"risk": "low"},
        },
        filters={"risk": "high"},
    )

    assert model["contract"] == "agent-ops-event/v1"
    assert model["summary"]["total_events"] == 1
    assert model["summary"]["blockers"] == 1
    assert model["sessions"][0]["status"] == "blocked"
    assert model["items"][0]["event_type"] == "tool_call"
