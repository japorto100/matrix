/**
 * Frontend Tools via CopilotKit AG-UI Protocol — exec-09 Phase 2.2
 *
 * Previously this was a hook. That was a bug: `useCopilotAction` reads
 * `useCopilotContext()` which throws "Remember to wrap your app in a
 * <CopilotKit>" when the runtime provider is absent. With our env-gated
 * AgentProviders (NEXT_PUBLIC_COPILOTKIT_ENABLED=false by default),
 * the provider isn't mounted and the hook crashed every page load.
 *
 * Fix: expose a `<FrontendToolsBridge>` component instead. The env-gate
 * happens in the outer component; the inner component (which actually calls
 * the CopilotKit hooks) only mounts when the provider is active.
 *
 * For backwards compat the previous hook-style API `useFrontendTools` is
 * kept but now returns the component (callers should render it).
 */

import { useCopilotAction } from "@copilotkit/react-core";

interface FrontendToolCallbacks {
	onSymbolChange: (symbol: string) => void;
	onTimeframeChange: (timeframe: string) => void;
	onPanelOpen: (panel: string) => void;
	onNavigate: (path: string) => void;
}

function FrontendToolsInner(props: FrontendToolCallbacks) {
	const { onSymbolChange, onTimeframeChange, onPanelOpen, onNavigate } = props;

	useCopilotAction({
		name: "set_chart_symbol",
		description: "Wechselt das aktive Chart-Symbol (z.B. 'EUR/USD', 'BTC/USD').",
		parameters: [{ name: "symbol", type: "string", description: "Trading symbol", required: true }],
		handler: ({ symbol }) => {
			onSymbolChange(symbol);
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
			onTimeframeChange(timeframe);
			return `Timeframe changed to ${timeframe}`;
		},
	});

	useCopilotAction({
		name: "open_panel",
		description: "Öffnet einen Sidebar-Tab (indicators, news, macro, orders, portfolio, strategy).",
		parameters: [{ name: "panel", type: "string", description: "Panel name", required: true }],
		handler: ({ panel }) => {
			onPanelOpen(panel);
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
			onNavigate(path);
			return `Navigated to ${path}`;
		},
	});

	return null;
}

/**
 * Bridge component that registers the four frontend AG-UI actions. Must be
 * rendered inside <CopilotKit>. The env-gate guards against running without
 * the provider (in which case useCopilotContext() would throw).
 */
export function FrontendToolsBridge(props: FrontendToolCallbacks) {
	const enabled = process.env.NEXT_PUBLIC_COPILOTKIT_ENABLED === "true";
	if (!enabled) return null;
	return <FrontendToolsInner {...props} />;
}
