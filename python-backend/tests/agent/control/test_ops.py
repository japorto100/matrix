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


def test_matrix_transport_blocker_is_first_class_ops_event():
    event = audit_event_to_ops_event(
        _audit_event(
            id=3,
            action="matrix_echo_loop_guard",
            tool_name="",
            success=True,
            metadata={
                "matrix_blocker": "echo_loop_blocked",
                "matrix_room_id": "!room:example.org",
                "matrix_event_id": "$event",
            },
        )
    )

    assert event["event_type"] == "matrix_transport"
    assert event["status"] == "blocked"
    assert event["blocker_reason"] == "echo_loop_blocked"
    assert event["matrix_room_id"] == "!room:example.org"
    assert event["matrix_event_id"] == "$event"


def test_matrix_approval_reaction_wait_maps_to_approval_lane():
    model = build_ops_read_model(
        audit_events=[
            _audit_event(
                id=4,
                action="matrix_approval_reaction_wait",
                tool_name="",
                success=True,
                metadata={
                    "room_id": "!room:example.org",
                    "event_id": "$approval",
                },
            )
        ],
        sessions=[
            {
                "thread_id": "thread-1",
                "role": "researcher",
                "checkpoint_count": 1,
                "is_active": False,
            }
        ],
    )

    assert model["items"][0]["event_type"] == "matrix_transport"
    assert model["items"][0]["status"] == "needs_approval"
    assert model["items"][0]["blocker_reason"] == "approval_reaction_wait"
    assert model["summary"]["approvals"] == 1
    assert model["sessions"][0]["status"] == "needs_approval"


def test_llm_request_telemetry_is_ops_event() -> None:
    event = audit_event_to_ops_event(
        _audit_event(
            id=5,
            action="llm_response",
            tool_name="",
            metadata={
                "request_telemetry": {
                    "contract": "provider-request-telemetry/v1",
                    "provider": "openrouter",
                    "model": "provider/model",
                    "prompt_digest": "abc",
                    "tool_catalog_digest": "tools",
                    "usage": {
                        "cache_read_tokens": 12,
                        "cache_write_tokens": 3,
                    },
                    "cache_break_reasons": ["tool_catalog_changed"],
                    "api_key": "secret",
                }
            },
        )
    )

    assert event["event_type"] == "llm"
    assert event["request_telemetry"]["provider"] == "openrouter"
    assert event["request_telemetry"]["api_key"] == "[redacted]"
    prompt_cache = event["linked_surfaces"]["prompt_cache"]
    assert prompt_cache["href"] == "/control/prompt-cache?thread_id=thread-1"
    assert prompt_cache["provider"] == "openrouter"
    assert prompt_cache["model"] == "provider/model"
    assert prompt_cache["cache_read_tokens"] == 12
    assert prompt_cache["cache_break_reasons"] == ["tool_catalog_changed"]


def test_report_artifact_refs_are_linked_from_ops_event() -> None:
    event = audit_event_to_ops_event(
        _audit_event(
            id=8,
            action="report_build",
            tool_name="report_build",
            output={
                "report_id": "risk-brief",
                "artifacts": {
                    "manifest": "/tmp/reports/risk-brief/manifest.json",
                    "html": "/tmp/reports/risk-brief/report.html",
                },
            },
            metadata={
                "runtime_events": [
                    {
                        "contract": "agent-runtime-event/v1",
                        "kind": "artifact",
                        "status": "completed",
                        "metadata": {"report_id": "risk-brief"},
                    }
                ]
            },
        )
    )

    report_links = event["linked_surfaces"]["report_artifacts"]
    assert report_links == [
        {
            "surface": "report_artifact",
            "label": "Report risk-brief",
            "href": "/control/reports?report_id=risk-brief",
            "report_id": "risk-brief",
            "manifest_path": "/tmp/reports/risk-brief/manifest.json",
            "output_path": "/tmp/reports/risk-brief/report.html",
            "status": "",
        }
    ]


def test_runtime_events_are_redacted_and_summarized() -> None:
    model = build_ops_read_model(
        audit_events=[
            _audit_event(
                id=6,
                action="llm_response",
                tool_name="",
                metadata={
                    "runtime_events": [
                        {
                            "contract": "agent-runtime-event/v1",
                            "kind": "llm",
                            "status": "completed",
                            "name": "llm_call",
                            "timestamp": "2026-04-29T12:00:01+00:00",
                            "metadata": {"api_key": "secret", "model": "provider/model"},
                        },
                        {
                            "contract": "agent-runtime-event/v1",
                            "kind": "memory",
                            "status": "blocked",
                            "name": "memory.retain.blocked",
                            "timestamp": "2026-04-29T12:00:00+00:00",
                        },
                    ]
                },
            )
        ],
        sessions=[],
    )

    assert model["summary"]["runtime_events"] == 2
    assert model["runtime_summary"]["by_kind"] == {"llm": 1, "memory": 1}
    assert model["runtime_summary"]["by_status"] == {"completed": 1, "blocked": 1}
    assert model["runtime_summary"]["latest"]["name"] == "llm_call"
    assert model["items"][0]["runtime_event_count"] == 2
    assert (
        model["items"][0]["runtime_events"][0]["metadata"]["api_key"] == "[redacted]"
    )
    assert model["items"][0]["runtime_events"][0]["audit_ref"] == "6"


def test_subagent_runtime_events_build_run_read_model() -> None:
    model = build_ops_read_model(
        audit_events=[
            _audit_event(
                id=7,
                action="route_decision",
                tool_name="",
                metadata={
                    "runtime_events": [
                        {
                            "contract": "agent-runtime-event/v1",
                            "kind": "subagent",
                            "status": "started",
                            "name": "subagent.delegation.started",
                            "thread_id": "thread-parent",
                            "timestamp": "2026-04-29T12:00:00+00:00",
                            "metadata": {
                                "child_task_id": "task-1",
                                "role": "researcher",
                                "delegate_kind": "domain",
                                "spawn_depth": 0,
                                "next_spawn_depth": 1,
                                "max_spawn_depth": 1,
                            },
                        },
                        {
                            "contract": "agent-runtime-event/v1",
                            "kind": "subagent",
                            "status": "completed",
                            "name": "subagent.delegation.completed",
                            "thread_id": "thread-parent",
                            "timestamp": "2026-04-29T12:00:01+00:00",
                            "metadata": {
                                "child_task_id": "task-1",
                                "role": "researcher",
                                "delegate_kind": "domain",
                                "spawn_depth": 0,
                                "next_spawn_depth": 1,
                                "max_spawn_depth": 1,
                                "result_digest": "sha256:child-result",
                            },
                        },
                        {
                            "contract": "agent-runtime-event/v1",
                            "kind": "memory",
                            "status": "accepted",
                            "name": "subagent.parent_memory_handoff",
                            "thread_id": "thread-parent",
                            "timestamp": "2026-04-29T12:00:02+00:00",
                            "metadata": {
                                "child_task_id": "task-1",
                                "child_session_id": "a2a-task-1",
                                "child_memory_write_allowed": False,
                                "parent_curated_memory_handoff": True,
                                "retain_decision": "parent_review_required",
                                "source_refs": ["a2a:task-1", "a2a-task-1"],
                                "confidence": "unverified_child_summary",
                                "result_digest": "sha256:child-result",
                            },
                        },
                    ]
                },
            )
        ],
        sessions=[],
    )

    assert model["summary"]["subagent_runs"] == 1
    run = model["subagent_runs"][0]
    assert run["child_task_id"] == "task-1"
    assert run["role"] == "researcher"
    assert run["status"] == "completed"
    assert run["ended_at"] == "2026-04-29T12:00:01+00:00"
    assert run["outcome"] == "ok"
    assert run["terminal_reason"] == "completed"
    assert run["is_terminal"] is True
    assert run["result_digest"] == "sha256:child-result"
    assert run["event_count"] == 3
    assert run["lifecycle_event_count"] == 2
    assert run["last_event_name"] == "subagent.delegation.completed"
    assert run["memory_handoff"] == {
        "available": True,
        "status": "accepted",
        "timestamp": "2026-04-29T12:00:02+00:00",
        "retain_decision": "parent_review_required",
        "child_memory_write_allowed": False,
        "parent_curated_memory_handoff": True,
        "confidence": "unverified_child_summary",
        "source_refs": ["a2a:task-1", "a2a-task-1"],
        "result_digest": "sha256:child-result",
        "output_digest": "",
    }
    assert run["controls"]["kill"] == "unsupported"
    assert run["controls"]["unsupported_reason"] == "non_durable_subagent_registry"


def test_subagent_timeout_runtime_event_closes_run_read_model() -> None:
    model = build_ops_read_model(
        audit_events=[
            _audit_event(
                id=9,
                action="route_decision",
                tool_name="",
                metadata={
                    "runtime_events": [
                        {
                            "contract": "agent-runtime-event/v1",
                            "kind": "subagent",
                            "status": "started",
                            "name": "subagent.delegation.started",
                            "thread_id": "thread-parent",
                            "timestamp": "2026-04-29T12:00:00+00:00",
                            "metadata": {
                                "child_task_id": "task-timeout",
                                "role": "researcher",
                                "delegate_kind": "domain",
                                "spawn_depth": 0,
                                "next_spawn_depth": 1,
                                "max_spawn_depth": 1,
                            },
                        },
                        {
                            "contract": "agent-runtime-event/v1",
                            "kind": "subagent",
                            "status": "stale",
                            "name": "subagent.delegation.timeout",
                            "thread_id": "thread-parent",
                            "timestamp": "2026-04-29T12:00:05+00:00",
                            "metadata": {
                                "child_task_id": "task-timeout",
                                "role": "researcher",
                                "delegate_kind": "domain",
                                "spawn_depth": 0,
                                "next_spawn_depth": 1,
                                "max_spawn_depth": 1,
                                "error": "node_timeout",
                            },
                        },
                    ]
                },
            )
        ],
        sessions=[],
    )

    run = model["subagent_runs"][0]
    assert run["status"] == "stale"
    assert run["outcome"] == "timeout"
    assert run["terminal_reason"] == "timeout"
    assert run["is_terminal"] is True
    assert run["ended_at"] == "2026-04-29T12:00:05+00:00"
    assert run["memory_handoff"] == {"available": False}
