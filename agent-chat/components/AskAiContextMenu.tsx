"use client";

// AC90: Reusable "Ask AI about this" context menu wrapper.
// Uses shadcn ContextMenu (Radix) — no manual position tracking needed.
// Usage: wrap any element with <AskAiContextMenu context="...">...</AskAiContextMenu>

import { Bot } from "lucide-react";
import {
	ContextMenu,
	ContextMenuContent,
	ContextMenuItem,
	ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useGlobalChat } from "@/features/agent-chat/context/GlobalChatContext";

interface AskAiContextMenuProps {
	/** Pre-built context string injected into chat when "Ask AI" is clicked */
	context: string;
	children: React.ReactNode;
	/** Optional additional menu items rendered after the default "Ask AI" entry */
	extraItems?: React.ReactNode;
}

export function AskAiContextMenu({ context, children, extraItems }: AskAiContextMenuProps) {
	const { openChat } = useGlobalChat();

	return (
		<ContextMenu>
			<ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
			<ContextMenuContent className="min-w-[180px]">
				<ContextMenuItem
					className="flex items-center gap-2 cursor-pointer"
					onClick={() => openChat(context)}
				>
					<Bot className="h-3.5 w-3.5 text-primary" />
					Ask AI about this
				</ContextMenuItem>
				{extraItems}
			</ContextMenuContent>
		</ContextMenu>
	);
}
