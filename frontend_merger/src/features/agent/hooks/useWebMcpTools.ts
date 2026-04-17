/**
 * WebMCP Tools Hook — exec-09 Phase 4
 *
 * Exponiert Trading-App Capabilities via navigator.modelContext (WebMCP / MCP-B).
 * Voraussetzung: @mcp-b/global Polyfill muss vorher importiert sein.
 */

import { useWebMCP } from "@mcp-b/react-webmcp";

interface WebMcpCallbacks {
	onSymbolChange: (symbol: string) => void;
	onTimeframeChange: (timeframe: string) => void;
	getChartState: () => { symbol: string; timeframe: string };
}

export function useWebMcpTools(callbacks: WebMcpCallbacks) {
	useWebMCP({
		name: "trading_get_chart_state",
		description: "Returns the chart symbol and timeframe the user is currently viewing.",
		inputSchema: { type: "object" as const, properties: {} },
		handler: async () => callbacks.getChartState(),
	});

	useWebMCP({
		name: "trading_set_symbol",
		description: "Changes the active trading chart symbol.",
		inputSchema: {
			type: "object" as const,
			properties: {
				symbol: { type: "string" as const, description: "Trading symbol (e.g. EUR/USD)" },
			},
			required: ["symbol"] as const,
		},
		handler: async (input: { symbol: string }) => {
			callbacks.onSymbolChange(input.symbol);
			return { ok: true, symbol: input.symbol };
		},
	});

	useWebMCP({
		name: "trading_set_timeframe",
		description: "Changes the chart timeframe.",
		inputSchema: {
			type: "object" as const,
			properties: {
				timeframe: { type: "string" as const, description: "Timeframe (1m, 5m, 1H, 4H, 1D)" },
			},
			required: ["timeframe"] as const,
		},
		handler: async (input: { timeframe: string }) => {
			callbacks.onTimeframeChange(input.timeframe);
			return { ok: true, timeframe: input.timeframe };
		},
	});
}
