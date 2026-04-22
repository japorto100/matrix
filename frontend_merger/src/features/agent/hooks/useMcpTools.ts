/**
 * MCP Tools Hook — exec-09 Phase 1.3
 *
 * Connects to the Python MCP Server (via Go Gateway /api/v1/mcp/)
 * using the `use-mcp` React hook. Provides standardised tool discovery
 * and calling for all TradingTools registered in the MCP Server.
 *
 * Backend-Tools (data/API) flow through MCP.
 * Frontend-Tools (UI mutations) stay in frontend-tools.ts (no backend roundtrip).
 */

import { useMcp } from "use-mcp/react";

const MCP_ENDPOINT = process.env.NEXT_PUBLIC_MCP_URL ?? "http://localhost:29318/api/v1/mcp";

export function useMcpTools() {
	const { tools, callTool, resources, state } = useMcp({
		url: MCP_ENDPOINT,
		clientConfig: { name: "agent-chat" },
	});

	return {
		/** All MCP tools discovered from the server */
		mcpTools: tools,
		/** Call a specific MCP tool by name with arguments */
		callMcpTool: callTool,
		/** MCP resources (data endpoints) */
		mcpResources: resources,
		/** Connection status */
		mcpStatus: state,
		/** Whether the MCP server is reachable */
		isConnected: state === "ready",
	};
}
