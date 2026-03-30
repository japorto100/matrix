"use client";

// AC75: GlobalChatOverlay — AgentChatPanel als shadcn Sheet (side=right, modal=false)
// AC89: Split-View mode — "sheet" = overlay, "split" = inline panel (pushes content)
// AC92: modal=false → Chart bleibt interaktiv in sheet mode

import { useCallback, useRef } from "react";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { AgentChatPanel } from "@/features/agent-chat/AgentChatPanel";
import { useGlobalChat } from "@/features/agent-chat/context/GlobalChatContext";

export function GlobalChatOverlay() {
	const { open, mode, closeChat } = useGlobalChat();
	const focusFnRef = useRef<(() => void) | null>(null);

	const handleOpenChange = useCallback(
		(next: boolean) => {
			if (!next) closeChat();
		},
		[closeChat],
	);

	const handleMounted = useCallback(
		(focusFn: () => void) => {
			focusFnRef.current = focusFn;
			if (open) focusFn();
		},
		[open],
	);

	// Split mode: inline panel in the layout flow (no Sheet overlay)
	if (mode === "split") {
		if (!open) return null;
		return (
			<div className="flex h-full w-[420px] shrink-0 flex-col border-l border-border bg-background">
				<AgentChatPanel onMounted={handleMounted} />
			</div>
		);
	}

	// Sheet mode (default): slides over content, chart stays interactive
	return (
		<Sheet open={open} onOpenChange={handleOpenChange} modal={false}>
			<SheetContent
				side="right"
				className="w-[420px] sm:w-[480px] p-0 flex flex-col border-l border-border"
				onPointerDownOutside={(e) => e.preventDefault()}
				onInteractOutside={(e) => e.preventDefault()}
			>
				<AgentChatPanel onMounted={handleMounted} />
			</SheetContent>
		</Sheet>
	);
}
