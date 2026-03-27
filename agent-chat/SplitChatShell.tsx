"use client";

// AC89: SplitChatShell — wraps page content; in split mode renders AgentChatPanel beside content
// AC93: in rail mode renders persistent 240px sidebar regardless of open state
// In sheet mode: renders children only (GlobalChatOverlay handles the overlay)

import type { ReactNode } from "react";
import { AgentChatPanel } from "@/features/agent-chat/AgentChatPanel";
import { useGlobalChat } from "@/features/agent-chat/context/GlobalChatContext";

export function SplitChatShell({ children }: { children: ReactNode }) {
	const { open, mode } = useGlobalChat();
	const isSplit = open && mode === "split";
	// AC93: rail is always shown when mode === "rail", independent of open state
	const isRail = mode === "rail";

	return (
		<div className="flex flex-1 overflow-hidden">
			<div className="flex flex-1 flex-col overflow-hidden">{children}</div>
			{isSplit && (
				<div className="flex w-[420px] shrink-0 flex-col border-l border-border bg-background">
					<AgentChatPanel />
				</div>
			)}
			{isRail && (
				<div className="flex w-[240px] shrink-0 flex-col border-l border-border bg-background">
					<AgentChatPanel />
				</div>
			)}
		</div>
	);
}
