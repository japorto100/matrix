"""Runtime preflight checks for live Meta-Harness runs."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
MEMORY_EVAL_CONTAINER = "matrix-memory-eval-postgres"
MEMORY_EVAL_PORT = 55433
DEFAULT_DOCKER_COMPOSE = Path(__file__).resolve().parents[2] / "docker-compose.memory-eval.yml"


@dataclass(frozen=True)
class RuntimePreflightResult:
    """Serializable outcome for the run artifact and CLI output."""

    enabled: bool
    command: str
    db_url_configured: bool
    db_env_key: str
    host: str
    port: int | None
    local_memory_eval_target: bool
    tcp_ready_before: bool
    auto_start_enabled: bool
    auto_start_attempted: bool
    auto_start_succeeded: bool
    tcp_ready_after: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)
    failures: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "command": self.command,
            "db_url_configured": self.db_url_configured,
            "db_env_key": self.db_env_key,
            "host": self.host,
            "port": self.port,
            "local_memory_eval_target": self.local_memory_eval_target,
            "tcp_ready_before": self.tcp_ready_before,
            "auto_start_enabled": self.auto_start_enabled,
            "auto_start_attempted": self.auto_start_attempted,
            "auto_start_succeeded": self.auto_start_succeeded,
            "tcp_ready_after": self.tcp_ready_after,
            "warnings": list(self.warnings),
            "failures": list(self.failures),
        }


def run_runtime_preflight(
    *,
    command: str = "",
    compose_file: Path = DEFAULT_DOCKER_COMPOSE,
    auto_start: bool | None = None,
    wait_seconds: float = 15.0,
    connect_timeout: float = 0.5,
) -> RuntimePreflightResult:
    """Check live-run dependencies and start the local eval DB when safe."""

    if _env_false("META_HARNESS_RUNTIME_PREFLIGHT"):
        return RuntimePreflightResult(
            enabled=False,
            command=command,
            db_url_configured=False,
            db_env_key="",
            host="",
            port=None,
            local_memory_eval_target=False,
            tcp_ready_before=False,
            auto_start_enabled=False,
            auto_start_attempted=False,
            auto_start_succeeded=False,
            tcp_ready_after=False,
        )

    db_env_key, db_url = _configured_db_url()
    warnings: list[str] = []
    failures: list[str] = []
    if not db_url:
        warnings.append(
            "AUDIT_DB_URL/HINDSIGHT_DB_URL not configured; trace persistence may fall back to JSONL."
        )
        return RuntimePreflightResult(
            enabled=True,
            command=command,
            db_url_configured=False,
            db_env_key="",
            host="",
            port=None,
            local_memory_eval_target=False,
            tcp_ready_before=False,
            auto_start_enabled=False,
            auto_start_attempted=False,
            auto_start_succeeded=False,
            tcp_ready_after=False,
            warnings=tuple(warnings),
        )

    host, port = _parse_db_endpoint(db_url)
    if not host or port is None:
        failures.append(f"{db_env_key} has no TCP host/port endpoint")
        return RuntimePreflightResult(
            enabled=True,
            command=command,
            db_url_configured=True,
            db_env_key=db_env_key,
            host=host,
            port=port,
            local_memory_eval_target=False,
            tcp_ready_before=False,
            auto_start_enabled=False,
            auto_start_attempted=False,
            auto_start_succeeded=False,
            tcp_ready_after=False,
            failures=tuple(failures),
        )

    tcp_ready_before = _tcp_ready(host, port, timeout=connect_timeout)
    local_memory_eval_target = _is_local_memory_eval_target(host, port)
    auto_start_enabled = _default_auto_start() if auto_start is None else bool(auto_start)
    auto_start_attempted = False
    auto_start_succeeded = False

    if not tcp_ready_before:
        if local_memory_eval_target and auto_start_enabled:
            auto_start_attempted = True
            auto_start_succeeded = _start_memory_eval_postgres(compose_file=compose_file)
        elif local_memory_eval_target:
            warnings.append("local memory-eval Postgres is down and auto-start is disabled")
        else:
            failures.append(
                f"{db_env_key} endpoint {host}:{port} is not reachable; refusing to guess a DB service"
            )

    tcp_ready_after = (
        True
        if tcp_ready_before
        else _wait_for_tcp(host, port, timeout=connect_timeout, wait_seconds=wait_seconds)
    )
    if not tcp_ready_after and local_memory_eval_target:
        failures.append(
            f"{MEMORY_EVAL_CONTAINER} did not become reachable on {host}:{port}"
        )

    return RuntimePreflightResult(
        enabled=True,
        command=command,
        db_url_configured=True,
        db_env_key=db_env_key,
        host=host,
        port=port,
        local_memory_eval_target=local_memory_eval_target,
        tcp_ready_before=tcp_ready_before,
        auto_start_enabled=auto_start_enabled,
        auto_start_attempted=auto_start_attempted,
        auto_start_succeeded=auto_start_succeeded,
        tcp_ready_after=tcp_ready_after,
        warnings=tuple(warnings),
        failures=tuple(failures),
    )


def ensure_runtime_preflight(**kwargs: Any) -> dict[str, Any]:
    """Run preflight and raise when live infrastructure is known-broken."""

    result = run_runtime_preflight(**kwargs)
    if result.failures:
        raise RuntimeError("; ".join(result.failures))
    return result.as_dict()


def write_runtime_preflight_artifact(
    *,
    data_dir: Path,
    run_id: str,
    result: dict[str, Any],
) -> None:
    path = data_dir / "runs" / run_id / "runtime_preflight.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_dumps(result), encoding="utf-8")


def _configured_db_url() -> tuple[str, str]:
    for key in ("AUDIT_DB_URL", "HINDSIGHT_DB_URL"):
        value = os.environ.get(key, "").strip()
        if value:
            return key, value
    return "", ""


def _parse_db_endpoint(db_url: str) -> tuple[str, int | None]:
    parsed = urlparse(db_url)
    host = parsed.hostname or ""
    port = parsed.port
    if port is None and parsed.scheme in {"postgres", "postgresql"}:
        port = 5432
    return host, port


def _is_local_memory_eval_target(host: str, port: int) -> bool:
    return host in LOCAL_HOSTS and port == MEMORY_EVAL_PORT


def _default_auto_start() -> bool:
    if _env_false("META_HARNESS_AUTO_START_DB"):
        return False
    if _env_true("META_HARNESS_AUTO_START_DB"):
        return True
    app_env = os.environ.get("APP_ENV", "").strip().lower()
    return app_env not in {"prod", "production"}


def _env_true(key: str) -> bool:
    return os.environ.get(key, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_false(key: str) -> bool:
    return os.environ.get(key, "").strip().lower() in {"0", "false", "no", "off"}


def _tcp_ready(host: str, port: int, *, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_tcp(host: str, port: int, *, timeout: float, wait_seconds: float) -> bool:
    deadline = time.monotonic() + max(wait_seconds, 0.0)
    while time.monotonic() <= deadline:
        if _tcp_ready(host, port, timeout=timeout):
            return True
        time.sleep(0.25)
    return False


def _start_memory_eval_postgres(*, compose_file: Path) -> bool:
    container_exists = _run(["podman", "container", "exists", MEMORY_EVAL_CONTAINER]).returncode == 0
    if container_exists:
        return _run(["podman", "start", MEMORY_EVAL_CONTAINER]).returncode == 0
    if compose_file.exists():
        return (
            _run(["podman", "compose", "-f", str(compose_file), "up", "-d", "postgres"]).returncode
            == 0
        )
    return False


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )


def _json_dumps(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value, indent=2, sort_keys=True) + "\n"
