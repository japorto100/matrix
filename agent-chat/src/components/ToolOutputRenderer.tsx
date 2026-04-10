/**
 * ToolOutputRenderer — exec-09 Generative UI in Chat
 *
 * Mappt Tool-Call Outputs auf Rich UI Components (Tambo Pattern).
 * Wenn ein Tool ein registriertes UI-Component hat, wird dieses gerendert
 * statt rohes JSON. Fallback: JSON bleibt fuer unbekannte Tools.
 */

import { Loader2 } from "lucide-react";
import type { ComponentType } from "react";
import { SandboxArtifact } from "./artifacts/SandboxArtifact";
import { ChartWidget } from "./tambo/ChartWidget";
import { PortfolioCard } from "./tambo/PortfolioCard";

// Tool-Name → React Component Mapping
const TOOL_RENDERERS: Record<string, ComponentType<any>> = {
	get_chart_state: ChartWidget,
	get_portfolio_summary: PortfolioCard,
	sandbox_execute: SandboxArtifact,    // exec-13 6.3: OpenSandbox Results
	file_analyze: SandboxArtifact,       // exec-12: File Analysis Results (same format)
};

/** Prueft ob ein Tool einen Rich Renderer hat */
export function hasRichRenderer(toolName: string): boolean {
	return toolName in TOOL_RENDERERS;
}

interface ToolOutputRendererProps {
	toolName: string;
	output: unknown;
}

/** Rendert Tool-Output als Rich UI Component wenn verfuegbar */
export function ToolOutputRenderer({ toolName, output }: ToolOutputRendererProps) {
	// exec-09: Browser-Tool Marker erkennen
	if (
		typeof output === "object" &&
		output !== null &&
		(output as any).action === "browser_execute"
	) {
		return (
			<div className="flex items-center gap-1.5 text-amber-400 text-[10px] mt-1">
				<Loader2 className="h-3 w-3 animate-spin" />
				<span>Executing in browser via WebMCP...</span>
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
