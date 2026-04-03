# Sandbox Configuration — exec-12 Phase 1.2
# Frozen dataclasses (follows AgentExecutionContext pattern).

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import timedelta


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
    """OpenSandbox Server URL. Docker Compose service name as default."""
    return os.environ.get("OPENSANDBOX_SERVER_URL", "http://opensandbox-server:8080")


def get_code_image() -> str:
    return os.environ.get("SANDBOX_CODE_IMAGE", "tradeview/sandbox-code-interpreter:v1")


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
