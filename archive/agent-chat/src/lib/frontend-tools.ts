/**
 * Agent Frontend-Tool-Registry — Phase 10.v3
 *
 * SOTA Pattern (MCP / WebMCP, März 2026):
 * Tools live where their effects are.
 *   - UI-Mutations  → Frontend-Tools (React-Callbacks, kein Backend-Roundtrip)
 *   - Daten/APIs    → Backend-Tools  (Go/Python, agent-service)
 *
 * Der Agent ruft Tools via tool_use auf. Das Chat-Panel nimmt die tool_use-Response,
 * findet das Tool im Registry, führt execute() aus (mit Confirm-Guard falls nötig).
 * Kein Backend-Roundtrip für reine UI-State-Änderungen.
 */

import type { FusionSymbol } from "@/lib/fusion-symbols";
import type { TimeframeValue } from "@/lib/providers/types";

// ─── Tool-Typen ──────────────────────────────────────────────────────────────

export type ConfirmLevel = "none" | "confirm";

export interface FrontendTool<TArgs = Record<string, unknown>> {
	name: string;
	description: string;
	/** Ob das Tool eine explizite User-Bestätigung braucht bevor es ausgeführt wird */
	confirmLevel: ConfirmLevel;
	execute: (args: TArgs, callbacks: FrontendToolCallbacks) => void | Promise<void>;
}

/** Callbacks die vom TradingWorkspace / page.tsx bereitgestellt werden */
export interface FrontendToolCallbacks {
	onSymbolChange: (symbol: FusionSymbol) => void;
	onTimeframeChange: (tf: TimeframeValue) => void;
	onPanelOpen: (
		panel: "indicators" | "news" | "macro" | "orders" | "portfolio" | "strategy",
	) => void;
	onNavigate: (path: string) => void;
}

// ─── Tool-Definitionen ───────────────────────────────────────────────────────

export const SET_CHART_SYMBOL: FrontendTool<{ symbol: string }> = {
	name: "set_chart_symbol",
	description: "Wechselt das aktive Chart-Symbol (z.B. 'EUR/USD', 'BTC/USD').",
	confirmLevel: "confirm",
	execute({ symbol }, { onSymbolChange }) {
		// Import dynamisch vermeiden — Caller injiziert passendes FusionSymbol-Objekt
		// Das Chat-Panel löst symbol → FusionSymbol auf bevor execute() gerufen wird
		// Caller is responsible for resolving a full FusionSymbol before execute().
		// Stub with required fields so the handler can at minimum update the symbol string.
		onSymbolChange({ symbol, name: symbol, basePrice: 0, type: "crypto" } as FusionSymbol);
	},
};

export const SET_TIMEFRAME: FrontendTool<{ timeframe: TimeframeValue }> = {
	name: "set_timeframe",
	description: "Wechselt den Timeframe des aktiven Charts.",
	confirmLevel: "confirm",
	execute({ timeframe }, { onTimeframeChange }) {
		onTimeframeChange(timeframe);
	},
};

export const OPEN_PANEL: FrontendTool<{
	panel: "indicators" | "news" | "macro" | "orders" | "portfolio" | "strategy";
}> = {
	name: "open_panel",
	description:
		"Öffnet einen bestimmten Sidebar-Tab (indicators, news, macro, orders, portfolio, strategy).",
	confirmLevel: "none",
	execute({ panel }, { onPanelOpen }) {
		onPanelOpen(panel);
	},
};

export const NAVIGATE_TO: FrontendTool<{ path: string }> = {
	name: "navigate_to",
	description: "Navigiert zu einer anderen Seite der App (z.B. '/geopolitical-map').",
	confirmLevel: "confirm",
	execute({ path }, { onNavigate }) {
		onNavigate(path);
	},
};

// ─── Registry ────────────────────────────────────────────────────────────────

type AnyFrontendTool = FrontendTool<Record<string, unknown>>;

export const FRONTEND_TOOL_REGISTRY: Record<string, AnyFrontendTool> = {
	[SET_CHART_SYMBOL.name]: SET_CHART_SYMBOL as AnyFrontendTool,
	[SET_TIMEFRAME.name]: SET_TIMEFRAME as AnyFrontendTool,
	[OPEN_PANEL.name]: OPEN_PANEL as AnyFrontendTool,
	[NAVIGATE_TO.name]: NAVIGATE_TO as AnyFrontendTool,
};

/** Gibt null zurück wenn das Tool nicht im Registry ist. */
export function resolveFrontendTool(name: string): FrontendTool | null {
	return FRONTEND_TOOL_REGISTRY[name] ?? null;
}
