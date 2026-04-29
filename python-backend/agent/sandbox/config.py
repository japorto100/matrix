# Sandbox Configuration — exec-12 Phase 1.2
# Frozen dataclasses (follows AgentExecutionContext pattern).

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta

from opensandbox.config import ConnectionConfig


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration for a sandbox instance."""

    image: str = ""  # Resolved via get_code_image() / get_browser_image()
    timeout: timedelta = timedelta(minutes=10)
    cpu: str = "1"
    memory: str = "2Gi"
    # Egress allowlist — empty tuple means no network access
    allowed_domains: tuple[str, ...] = ()
    # Entrypoint for the sandbox container
    entrypoint: tuple[str, ...] = ("/opt/opensandbox/code-interpreter.sh",)


def get_sandbox_server_url() -> str:
    """OpenSandbox server URL for health checks and diagnostics."""
    return (
        os.environ.get("OPENSANDBOX_SERVER_URL")
        or os.environ.get("OPEN_SANDBOX_URL")
        or "http://localhost:8080"
    )


def get_sandbox_connection_config() -> ConnectionConfig:
    """ConnectionConfig for the OpenSandbox Python SDK.

    The SDK reads OPEN_SANDBOX_DOMAIN, while older Matrix env files used
    OPENSANDBOX_SERVER_URL/OPEN_SANDBOX_URL. Normalize those names here so the
    agent and health checks target the same server.
    """
    domain = (
        os.environ.get("OPEN_SANDBOX_DOMAIN")
        or os.environ.get("OPENSANDBOX_SERVER_URL")
        or os.environ.get("OPEN_SANDBOX_URL")
        or "http://localhost:8080"
    )
    request_timeout = float(os.environ.get("OPENSANDBOX_REQUEST_TIMEOUT_SEC", "180"))
    use_server_proxy = _env_bool("OPENSANDBOX_USE_SERVER_PROXY", default=True)
    return ConnectionConfig(
        domain=domain,
        request_timeout=timedelta(seconds=request_timeout),
        use_server_proxy=use_server_proxy,
    )


def get_sandbox_ready_timeout() -> timedelta:
    """Maximum time to wait for a created sandbox to become usable."""
    return timedelta(seconds=float(os.environ.get("OPENSANDBOX_READY_TIMEOUT_SEC", "90")))


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_code_image() -> str:
    return os.environ.get(
        "SANDBOX_CODE_IMAGE",
        "sandbox-registry.cn-zhangjiakou.cr.aliyuncs.com/opensandbox/code-interpreter:v1.0.2",
    )


def get_browser_image() -> str:
    return os.environ.get("SANDBOX_BROWSER_IMAGE", "tradeview/sandbox-browser:v1")


# ── Preset Configs ─────────────────────────────────────────────────────────

CODE_SANDBOX = SandboxConfig(
    image=get_code_image(),
    timeout=timedelta(minutes=10),
    cpu="1",
    memory="2Gi",
)

BACKTEST_SANDBOX = SandboxConfig(
    image=get_code_image(),
    timeout=timedelta(minutes=30),
    cpu="2",
    memory="4Gi",
)

BROWSER_SANDBOX = SandboxConfig(
    image=get_browser_image(),
    timeout=timedelta(minutes=10),
    cpu="1",
    memory="2Gi",
    allowed_domains=(
        "*.reuters.com",
        "*.bloomberg.com",
        "*.tradingview.com",
        "*.coindesk.com",
        "*.yahoo.com",
    ),
)
