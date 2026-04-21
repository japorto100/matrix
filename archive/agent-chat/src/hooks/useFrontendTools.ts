/**
 * Frontend Tools via CopilotKit AG-UI Protocol — exec-09 Phase 2.2
 *
 * Ersetzt das eigene FrontendTool Interface (lib/frontend-tools.ts)
 * mit dem standardisierten CopilotKit useCopilotAction() Pattern.
 *
 * Agent steuert Frontend-State via AG-UI Protocol:
 *   - SET_CHART_SYMBOL → Agent wechselt Chart-Symbol
 *   - SET_TIMEFRAME → Agent wechselt Timeframe
 *   - OPEN_PANEL → Agent öffnet Sidebar-Tab
 *   - NAVIGATE_TO → Agent navigiert zu anderer Page
 */

import { useCopilotAction } from "@copilotkit/react-core";

interface FrontendToolCallbacks {
	onSymbolChange: (symbol: string) => void;
	onTimeframeChange: (timeframe: string) => void;
	onPanelOpen: (panel: string) => void;
	onNavigate: (path: string) => void;
}

export function useFrontendTools(callbacks: FrontendToolCallbacks) {
	useCopilotAction({
		name: "set_chart_symbol",
		description: "Wechselt das aktive Chart-Symbol (z.B. 'EUR/USD', 'BTC/USD').",
		parameters: [{ name: "symbol", type: "string", description: "Trading symbol", required: true }],
		handler: ({ symbol }) => {
			callbacks.onSymbolChange(symbol);
			return `Chart symbol changed to ${symbol}`;
		},
	});

	useCopilotAction({
		name: "set_timeframe",
		description: "Wechselt den Timeframe des aktiven Charts.",
		parameters: [
			{
				name: "timeframe",
				type: "string",
				description: "Timeframe value (1m, 5m, 1H, 4H, 1D)",
				required: true,
			},
		],
		handler: ({ timeframe }) => {
			callbacks.onTimeframeChange(timeframe);
			return `Timeframe changed to ${timeframe}`;
		},
	});

	useCopilotAction({
		name: "open_panel",
		description: "Öffnet einen Sidebar-Tab (indicators, news, macro, orders, portfolio, strategy).",
		parameters: [{ name: "panel", type: "string", description: "Panel name", required: true }],
		handler: ({ panel }) => {
			callbacks.onPanelOpen(panel);
			return `Panel ${panel} opened`;
		},
	});

	useCopilotAction({
		name: "navigate_to",
		description: "Navigiert zu einer anderen Seite der App.",
		parameters: [
			{
				name: "path",
				type: "string",
				description: "Route path (e.g. /geopolitical-map)",
				required: true,
			},
		],
		handler: ({ path }) => {
			callbacks.onNavigate(path);
			return `Navigated to ${path}`;
		},
	});
}
