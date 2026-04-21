"use client";

import { MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

export function Reactions({
	reactions,
	myReactions,
	onReact,
	eventId,
}: {
	reactions: Record<string, number>;
	myReactions?: Record<string, string>;
	onReact?: (eventId: string, emoji: string, myReactions?: Record<string, string>) => void;
	eventId: string;
}) {
	const entries = Object.entries(reactions);
	if (entries.length === 0) return null;
	return (
		<div className="flex flex-wrap gap-1 mt-1">
			{entries.map(([emoji, count]) => {
				const isMine = !!myReactions?.[emoji];
				return (
					<button
						key={emoji}
						type="button"
						className={cn(
							"inline-flex items-center gap-1 rounded-full px-2 py-1 text-sm transition-colors",
							isMine ? "bg-primary/20 hover:bg-destructive/20 cursor-pointer" : "bg-muted/60",
						)}
						title={isMine ? "Reaktion entfernen" : emoji}
						onClick={() => {
							if (onReact && isMine) onReact(eventId, emoji, myReactions);
						}}
					>
						<span className="text-base">{emoji}</span>
						{count > 1 && (
							<span className="text-xs text-muted-foreground font-medium">{count}</span>
						)}
					</button>
				);
			})}
		</div>
	);
}

export function ThreadChip({
	count,
	onOpen,
	isOwn,
}: {
	count: number;
	onOpen: () => void;
	isOwn: boolean;
}) {
	return (
		<button
			type="button"
			onClick={onOpen}
			className={cn(
				"mt-1 flex items-center gap-1 text-xs font-medium text-primary hover:underline",
				isOwn && "self-end",
			)}
		>
			<MessageSquare className="h-3 w-3" />
			{count} {count === 1 ? "Antwort" : "Antworten"}
		</button>
	);
}
