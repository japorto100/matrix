/**
 * WebMCP Bridge — exec-09 Phase 4
 *
 * Bruecke zwischen Browser WebMCP Tools und unserem Backend-Agent.
 * Sammelt alle via navigator.modelContext registrierten Tools und
 * macht sie dem Backend-Agent verfuegbar.
 *
 * Flow:
 * 1. Browser: Pages registrieren Tools via useWebMCPTool / navigator.modelContext
 * 2. Bridge: Sammelt Tool-Liste, schickt sie als Teil des Chat-Requests ans Backend
 * 3. Backend: Agent sieht Browser-Tools als aufrufbar
 * 4. Backend: Agent ruft Browser-Tool auf → Request kommt zurueck an Bridge
 * 5. Bridge: navigator.modelContext.callTool() → Result ans Backend
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface BrowserTool {
	name: string;
	description: string;
	inputSchema: Record<string, unknown>;
}

export interface WebMcpBridgeReturn {
	/** Alle aktuell im Browser registrierten WebMCP Tools */
	browserTools: BrowserTool[];
	/** Tool-Definitionen im Anthropic-Format fuer den Agent */
	toolDefinitions: Array<{
		name: string;
		description: string;
		input_schema: Record<string, unknown>;
	}>;
	/** Fuehrt ein Browser-Tool aus (vom Backend-Agent aufgerufen via SSE) */
	executeBrowserTool: (name: string, input: Record<string, unknown>) => Promise<unknown>;
	/** Ob navigator.modelContext verfuegbar ist */
	isAvailable: boolean;
}

export function useWebMcpBridge(): WebMcpBridgeReturn {
	const [browserTools, setBrowserTools] = useState<BrowserTool[]>([]);
	const [isAvailable, setIsAvailable] = useState(false);
	const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

	// Poll navigator.modelContext fuer registrierte Tools
	// (Tools koennen sich dynamisch aendern wenn User die Page wechselt)
	useEffect(() => {
		const mc = (navigator as any).modelContext;
		if (!mc) {
			setIsAvailable(false);
			return;
		}
		setIsAvailable(true);

		async function discover() {
			try {
				const mc = (navigator as any).modelContext;
				if (!mc?.listTools) return;
				const tools = await mc.listTools();
				const mapped: BrowserTool[] = (tools ?? []).map((t: any) => ({
					name: t.name ?? "",
					description: t.description ?? "",
					inputSchema: t.inputSchema ?? {},
				}));
				setBrowserTools(mapped);
			} catch {
				// Polyfill might not be ready yet
			}
		}

		// Initial discovery + poll alle 5s (Tools koennen sich aendern)
		void discover();
		pollRef.current = setInterval(() => void discover(), 5000);

		return () => {
			if (pollRef.current) clearInterval(pollRef.current);
		};
	}, []);

	// Tool-Definitionen im Anthropic-Format (fuer Python Agent Loop)
	const toolDefinitions = browserTools.map((t) => ({
		name: `browser_${t.name}`,
		description: `[Browser Tool] ${t.description}`,
		input_schema: t.inputSchema,
	}));

	// Browser-Tool ausfuehren (aufgerufen wenn Backend-Agent ein browser_* Tool called)
	const executeBrowserTool = useCallback(
		async (name: string, input: Record<string, unknown>): Promise<unknown> => {
			const mc = (navigator as any).modelContext;
			if (!mc?.callTool) {
				throw new Error("navigator.modelContext not available");
			}
			// Strip "browser_" Prefix — Backend sendet "browser_trading_set_symbol",
			// WebMCP kennt es als "trading_set_symbol"
			const toolName = name.startsWith("browser_") ? name.slice(8) : name;
			const result = await mc.callTool(toolName, input);
			return result;
		},
		[],
	);

	return {
		browserTools,
		toolDefinitions,
		executeBrowserTool,
		isAvailable,
	};
}
