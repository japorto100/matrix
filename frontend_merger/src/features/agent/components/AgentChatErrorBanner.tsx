"use client";

import { AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AgentChatErrorBannerProps {
	message: string;
	onDismiss: () => void;
}

export function AgentChatErrorBanner({ message, onDismiss }: AgentChatErrorBannerProps) {
	return (
		<div className="mx-3 mb-1.5 flex items-center gap-2 rounded border border-destructive/30 bg-destructive/10 px-3 py-1.5 text-xs text-destructive shrink-0">
			<AlertCircle className="h-3.5 w-3.5 shrink-0" />
			<span className="flex-1 line-clamp-2">{message}</span>
			<Button
				variant="ghost"
				size="icon"
				className="h-5 w-5 shrink-0 text-destructive hover:text-destructive"
				onClick={onDismiss}
			>
				<X className="h-3 w-3" />
			</Button>
		</div>
	);
}
