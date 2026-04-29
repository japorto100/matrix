"""MCP gateway policy primitives."""

from agent.mcp_gateway.policy import (
    McpCatalogEntry,
    McpServerConfig,
    McpToolDescriptorSnapshot,
    build_effective_catalog,
    diff_descriptor_snapshots,
    evaluate_resource_fetch_policy,
    evaluate_token_passthrough,
    evaluate_tool_invocation_policy,
    normalize_tool_name,
    snapshot_descriptor,
)

__all__ = [
    "McpCatalogEntry",
    "McpServerConfig",
    "McpToolDescriptorSnapshot",
    "build_effective_catalog",
    "diff_descriptor_snapshots",
    "evaluate_resource_fetch_policy",
    "evaluate_tool_invocation_policy",
    "evaluate_token_passthrough",
    "normalize_tool_name",
    "snapshot_descriptor",
]
