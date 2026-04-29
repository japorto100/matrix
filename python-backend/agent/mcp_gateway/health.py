"""MCP server health probes that do not invoke model-visible tools."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Any, Literal
from urllib.parse import urlparse

from agent.mcp_gateway.policy import McpServerConfig

HealthStatus = Literal["healthy", "unhealthy", "disabled"]
HealthProbe = Callable[[McpServerConfig], bool | Awaitable[bool]]


@dataclass(frozen=True)
class McpHealthProbeResult:
    server_id: str
    status: HealthStatus
    reason: str
    transport: str
    model_visible_tools_invoked: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


async def probe_mcp_server_health(
    server: McpServerConfig,
    *,
    probe: HealthProbe | None = None,
) -> McpHealthProbeResult:
    """Check transport/config reachability without listing or invoking tools."""

    if not server.enabled:
        return _result(server, "disabled", "server-disabled")
    config_error = _static_config_error(server)
    if config_error:
        return _result(server, "unhealthy", config_error)
    if probe is None:
        return _result(server, "healthy", "static-config-healthy")
    try:
        ok = probe(server)
        if hasattr(ok, "__await__"):
            ok = await ok  # type: ignore[assignment]
    except Exception as exc:  # noqa: BLE001
        return _result(server, "unhealthy", f"probe-error:{exc.__class__.__name__}")
    if ok:
        return _result(server, "healthy", "probe-healthy")
    return _result(server, "unhealthy", "probe-unhealthy")


def fixture_mcp_server_config(
    *,
    server_id: str = "fixture-mcp",
    enabled: bool = True,
) -> McpServerConfig:
    """Deterministic local fixture config for gateway tests."""

    return McpServerConfig(
        server_id=server_id,
        display_name="Fixture MCP",
        transport="streamable-http",
        url="http://127.0.0.1:18095/mcp",
        provenance_url="http://127.0.0.1:18095/about",
        enabled=enabled,
        trusted_server_ids=(server_id,),
    )


def fixture_mcp_descriptors() -> list[dict[str, Any]]:
    """Stable descriptor set used by policy and health tests."""

    return [
        {
            "name": "fixture_lookup",
            "description": "Read-only deterministic fixture lookup.",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        },
        {
            "name": "fixture_widget",
            "description": "Return deterministic widget metadata for policy tests.",
            "inputSchema": {"type": "object"},
            "_meta": {"widget_url": "https://fixture.example/widgets/summary"},
        },
    ]


def _static_config_error(server: McpServerConfig) -> str:
    if server.transport == "stdio":
        if not server.command:
            return "missing-command"
        return ""
    if server.transport in {"streamable-http", "sse", "http"}:
        if not server.url:
            return "missing-url"
        parsed = urlparse(server.url)
        if parsed.scheme not in {"http", "https"}:
            return "unsupported-url-scheme"
        if not parsed.hostname:
            return "missing-url-host"
        return ""
    return "unsupported-transport"


def _result(
    server: McpServerConfig,
    status: HealthStatus,
    reason: str,
) -> McpHealthProbeResult:
    return McpHealthProbeResult(
        server_id=server.server_id,
        status=status,
        reason=reason,
        transport=server.transport,
        model_visible_tools_invoked=False,
    )
