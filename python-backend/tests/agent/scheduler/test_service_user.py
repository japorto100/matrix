"""Quick cross-language parity checks for scheduler constants."""

from __future__ import annotations

import os

from agent.scheduler import (
    DEFAULT_JETSTREAM_STREAM,
    DEFAULT_QUEUE_GROUP,
    DEFAULT_SERVICE_USER_ID,
    SUBJECT_HEARTBEAT,
    SUBJECT_JOB_EXECUTE,
    is_service_user,
    jetstream_stream,
    queue_group,
    service_user_id,
)


def test_default_constants_match_go_side():
    # These MUST stay in lockstep with
    # go-appservice/internal/scheduler/scheduler.go.
    assert DEFAULT_SERVICE_USER_ID == "scheduler-service"
    assert DEFAULT_JETSTREAM_STREAM == "SCHEDULER"
    assert DEFAULT_QUEUE_GROUP == "scheduler-exec"
    assert SUBJECT_JOB_EXECUTE == "matrix.scheduler.job.execute"
    assert SUBJECT_HEARTBEAT == "matrix.scheduler.heartbeat"


def test_service_user_id_fallback(monkeypatch):
    monkeypatch.delenv("SCHEDULER_SERVICE_USER_ID", raising=False)
    assert service_user_id() == DEFAULT_SERVICE_USER_ID


def test_service_user_id_override(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SERVICE_USER_ID", "custom-svc")
    assert service_user_id() == "custom-svc"


def test_is_service_user_matches(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SERVICE_USER_ID", "svc-1")
    assert is_service_user("svc-1") is True
    assert is_service_user("regular-user") is False
    assert is_service_user("") is False
    assert is_service_user(None) is False


def test_jetstream_overrides(monkeypatch):
    monkeypatch.setenv("SCHEDULER_JETSTREAM_STREAM", "TEST_STREAM")
    monkeypatch.setenv("SCHEDULER_QUEUE_GROUP", "test-group")
    assert jetstream_stream() == "TEST_STREAM"
    assert queue_group() == "test-group"
    # cleanup so downstream tests in-session see defaults
    os.environ.pop("SCHEDULER_JETSTREAM_STREAM", None)
    os.environ.pop("SCHEDULER_QUEUE_GROUP", None)
