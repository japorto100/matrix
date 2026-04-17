"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import type { ReactNode } from "react";
import { queryClient } from "@/lib/query-client";

/**
 * Merged Providers for frontend_merger.
 *
 * Combines:
 *   - ThemeProvider (next-themes) — aus nextjs-chat, 4 Themes (light/dark/blue-dark/green-dark)
 *   - QueryClientProvider — geteilt von nextjs-chat + control-ui
 *   - NuqsAdapter — aus agent-chat (URL-State fuer chatId, symbol, timeframe etc.)
 *
 * Agent-spezifische Provider (CopilotKit, TamboProvider) laufen lokal in
 * `features/agent/AgentProviders.tsx` und werden nur auf /agent gemountet.
 */
export function Providers({ children }: { children: ReactNode }) {
	return (
		<ThemeProvider
			attribute="class"
			defaultTheme="dark"
			themes={["light", "dark", "blue-dark", "green-dark"]}
			disableTransitionOnChange
		>
			<QueryClientProvider client={queryClient}>
				<NuqsAdapter>{children}</NuqsAdapter>
			</QueryClientProvider>
		</ThemeProvider>
	);
}
