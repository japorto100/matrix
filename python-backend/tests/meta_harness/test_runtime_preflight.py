from __future__ import annotations

import subprocess

from meta_harness import runtime_preflight


def test_runtime_preflight_no_db_warns_without_failing(monkeypatch):
    monkeypatch.delenv("AUDIT_DB_URL", raising=False)
    monkeypatch.delenv("HINDSIGHT_DB_URL", raising=False)

    result = runtime_preflight.run_runtime_preflight(command="run")

    assert result.db_url_configured is False
    assert result.failures == ()
    assert result.warnings


def test_runtime_preflight_autostarts_local_memory_eval(monkeypatch, tmp_path):
    calls: list[list[str]] = []
    tcp_checks = iter([False, True])

    monkeypatch.delenv("AUDIT_DB_URL", raising=False)
    monkeypatch.setenv(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres:postgres@127.0.0.1:55433/hindsight_dev",
    )
    monkeypatch.setattr(
        runtime_preflight,
        "_tcp_ready",
        lambda host, port, *, timeout: next(tcp_checks),
    )

    def _fake_run(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(runtime_preflight, "_run", _fake_run)

    result = runtime_preflight.run_runtime_preflight(
        command="outer-loop",
        compose_file=tmp_path / "missing-compose.yml",
        wait_seconds=0.1,
    )

    assert result.local_memory_eval_target is True
    assert result.auto_start_attempted is True
    assert result.auto_start_succeeded is True
    assert result.tcp_ready_after is True
    assert calls == [
        ["podman", "container", "exists", "matrix-memory-eval-postgres"],
        ["podman", "start", "matrix-memory-eval-postgres"],
    ]


def test_runtime_preflight_fails_unknown_unreachable_db(monkeypatch):
    monkeypatch.delenv("AUDIT_DB_URL", raising=False)
    monkeypatch.setenv(
        "HINDSIGHT_DB_URL",
        "postgresql://postgres:postgres@127.0.0.1:5433/hindsight_dev",
    )
    monkeypatch.setattr(
        runtime_preflight,
        "_tcp_ready",
        lambda host, port, *, timeout: False,
    )

    result = runtime_preflight.run_runtime_preflight(command="outer-loop", wait_seconds=0.0)

    assert result.local_memory_eval_target is False
    assert result.failures
    assert "refusing to guess" in result.failures[0]


def test_ensure_runtime_preflight_raises_on_failure(monkeypatch):
    monkeypatch.setattr(
        runtime_preflight,
        "run_runtime_preflight",
        lambda **kwargs: runtime_preflight.RuntimePreflightResult(
            enabled=True,
            command="outer-loop",
            db_url_configured=True,
            db_env_key="HINDSIGHT_DB_URL",
            host="127.0.0.1",
            port=5433,
            local_memory_eval_target=False,
            tcp_ready_before=False,
            auto_start_enabled=False,
            auto_start_attempted=False,
            auto_start_succeeded=False,
            tcp_ready_after=False,
            failures=("db down",),
        ),
    )

    try:
        runtime_preflight.ensure_runtime_preflight(command="outer-loop")
    except RuntimeError as exc:
        assert "db down" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
