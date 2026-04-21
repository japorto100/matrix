/**
 * ToolOutputRenderer — exec-09 Generative UI in Chat
 *
 * Maps Tool-Call Outputs to Rich UI Components. When a tool has a registered
 * UI component it is rendered instead of raw JSON. Fallback: JSON for unknown
 * tools.
 *
 * Ansatz Y: the virtual `render_a2ui_surface` tool-result is validated against
 * a whitelisted schema and dispatched to the A2UI renderer.
 */

import { parseA2uiEnvelope } from "@agent/lib/a2uiTreeSchema";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { ComponentType } from "react";
import { A2uiMessageRenderer } from "./A2uiMessageRenderer";
import { ChartWidget } from "./a2ui/ChartWidget";
import { PortfolioCard } from "./a2ui/PortfolioCard";
import { SandboxArtifact } from "./artifacts/SandboxArtifact";

// Tool-Name → React Component Mapping
// biome-ignore lint/suspicious/noExplicitAny: tool output props vary per renderer
const TOOL_RENDERERS: Record<string, ComponentType<any>> = {
	get_chart_state: ChartWidget,
	get_portfolio_summary: PortfolioCard,
	sandbox_execute: SandboxArtifact,
	file_analyze: SandboxArtifact,
};

const RICH_RENDERER_NAMES = new Set<string>(["render_a2ui_surface"]);

/** Returns true if the tool has a rich UI renderer (keyed catalog or A2UI). */
export function hasRichRenderer(toolName: string): boolean {
	return toolName in TOOL_RENDERERS || RICH_RENDERER_NAMES.has(toolName);
}

interface ToolOutputRendererProps {
	toolName: string;
	output: unknown;
}

export function ToolOutputRenderer({ toolName, output }: ToolOutputRendererProps) {
	// exec-09: browser-tool marker
	if (
		typeof output === "object" &&
		output !== null &&
		(output as Record<string, unknown>).action === "browser_execute"
	) {
		return (
			<div className="mt-1 flex items-center gap-1.5 text-amber-400 text-[10px]">
				<Loader2 className="h-3 w-3 animate-spin" />
				<span>Executing in browser via WebMCP...</span>
			</div>
		);
	}

	// Ansatz Y: A2UI widget tree via virtual tool-result
	if (toolName === "render_a2ui_surface") {
		const parsed = parseA2uiEnvelope(output);
		if (!parsed.ok) {
			return (
				<div className="mt-1 flex items-center gap-1.5 rounded border border-red-500/20 bg-red-500/5 p-2 text-red-400 text-[10px]">
					<AlertTriangle className="h-3 w-3" />
					<span>Invalid A2UI payload: {parsed.error}</span>
				</div>
			);
		}
		return (
			<div className="mt-1">
				<A2uiMessageRenderer surfaceId={parsed.surfaceId} inlineTree={parsed.tree} />
			</div>
		);
	}

	const Component = TOOL_RENDERERS[toolName];
	if (!Component || typeof output !== "object" || output === null) {
		return (
			<pre className="whitespace-pre-wrap break-all text-[10px]">
				{JSON.stringify(output, null, 2)}
			</pre>
		);
	}

	return (
		<div className="mt-1">
			<Component {...(output as Record<string, unknown>)} />
		</div>
	);
}
