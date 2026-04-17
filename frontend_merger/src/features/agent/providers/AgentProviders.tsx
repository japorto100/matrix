/**
 * Agent Providers — exec-09
 *
 * Wraps Agent Chat with all protocol providers:
 * - CopilotKit (AG-UI Protocol for frontend-state mutations)
 * - Tambo (Generative UI component rendering)
 *
 * MCP (use-mcp) is a hook, not a provider — used directly in components.
 */

"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { TamboProvider } from "@tambo-ai/react";
import type { ReactNode } from "react";
import { tamboComponents } from "../components/tambo/registry";

interface AgentProvidersProps {
	children: ReactNode;
}

export function AgentProviders({ children }: AgentProvidersProps) {
	return (
		<CopilotKit
			runtimeUrl="/api/copilotkit"
			showDevConsole={process.env.NODE_ENV === "development"}
		>
			<TamboProvider
				apiKey={process.env.NEXT_PUBLIC_TAMBO_API_KEY ?? ""}
				components={tamboComponents}
			>
				{children}
			</TamboProvider>
		</CopilotKit>
	);
}
