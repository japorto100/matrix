/**
 * Agent Providers — exec-09 (v2: Tambo removed, A2UI target)
 *
 * Wraps Agent Chat with protocol providers:
 * - CopilotKit (AG-UI Protocol for frontend-state mutations) — opt-in via env
 *
 * Tambo entfernt 2026-04-21 — ersetzt durch Google A2UI v0.9 (Std-Spec für
 * generative UI widgets; matched unser python-agent Workflow via SDK).
 *
 * MCP (use-mcp) ist hook, nicht provider. A2UI-renderer läuft ohne provider.
 *
 * Env-flags:
 *   NEXT_PUBLIC_COPILOTKIT_ENABLED=true        → CopilotKit wrap aktiv
 *   NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL=<url>   → runtime-URL (default: leer = dry-mode)
 * Default OFF — children direkt gerendert, keine background retries.
 */

"use client";

import { CopilotKit } from "@copilotkit/react-core";
import type { ReactNode } from "react";
import { A2uiRootProvider } from "./A2uiProvider";
import { GlobalCopilotContext } from "./GlobalCopilotContext";

interface AgentProvidersProps {
	children: ReactNode;
}

export function AgentProviders({ children }: AgentProvidersProps) {
	const copilotEnabled = process.env.NEXT_PUBLIC_COPILOTKIT_ENABLED === "true";
	const copilotRuntimeUrl = process.env.NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL;

	// A2UI wraps everything (renderer is always available, even without backend —
	// just no surfaces rendered until python-agent streams widget-messages).
	// GlobalCopilotContext is innermost — self-gated so it no-ops without CopilotKit.
	let tree: ReactNode = (
		<A2uiRootProvider>
			<GlobalCopilotContext>{children}</GlobalCopilotContext>
		</A2uiRootProvider>
	);

	// CopilotKit only if env-opted-in AND runtime-URL configured.
	// Otherwise CopilotKit would retry /api/copilotkit → 404 → blocks dev UX.
	if (copilotEnabled && copilotRuntimeUrl) {
		tree = (
			<CopilotKit
				runtimeUrl={copilotRuntimeUrl}
				showDevConsole={process.env.NODE_ENV === "development"}
			>
				{tree}
			</CopilotKit>
		);
	}

	return <>{tree}</>;
}
