"""MCP gateway policy primitives."""

from agent.mcp_gateway.execution import (
    McpGatewayExecutionConfig,
    McpGatewayExecutionResult,
    McpToolCallRequest,
    execute_mcp_tool_call,
)
from agent.mcp_gateway.policy import (
    McpCatalogEntry,
    McpServerConfig,
    McpSessionGrant,
    McpToolDescriptorSnapshot,
    build_effective_catalog,
    diff_descriptor_snapshots,
    evaluate_resource_fetch_policy,
    evaluate_session_grant,
    evaluate_token_passthrough,
    evaluate_tool_invocation_policy,
    issue_session_grant,
    normalize_tool_name,
    snapshot_descriptor,
    tool_provenance,
)

__all__ = [
    "McpCatalogEntry",
    "McpGatewayExecutionConfig",
    "McpGatewayExecutionResult",
    "McpServerConfig",
    "McpSessionGrant",
    "McpToolCallRequest",
    "McpToolDescriptorSnapshot",
    "build_effective_catalog",
    "diff_descriptor_snapshots",
    "evaluate_resource_fetch_policy",
    "evaluate_session_grant",
    "evaluate_tool_invocation_policy",
    "evaluate_token_passthrough",
    "execute_mcp_tool_call",
    "issue_session_grant",
    "normalize_tool_name",
    "snapshot_descriptor",
    "tool_provenance",
]
