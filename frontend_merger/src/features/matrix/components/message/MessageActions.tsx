"use client";

import type { ResolvedMessage } from "@matrix/lib/types";
import { MessageSquare, Pencil, Pin, PinOff, Reply, Share, SmilePlus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const QUICK_REACTIONS = ["👍", "👎", "😂", "🔥", "😮", "😢"];

export interface MessageActionProps {
	message: ResolvedMessage;
	onReact?: (eventId: string, emoji: string, myReactions?: Record<string, string>) => void;
	onReply?: (eventId: string, sender: string, body: string) => void;
	onEdit?: (eventId: string, body: string) => void;
	onRedact?: (eventId: string) => void;
	onForward?: (body: string, senderName: string) => void;
	onPin?: (eventId: string) => void;
	onThreadOpen?: (eventId: string) => void;
	isPinned?: boolean;
}

export function MessageActions({
	message,
	onReact,
	onReply,
	onEdit,
	onRedact,
	onForward,
	onPin,
	onThreadOpen,
	isPinned,
}: MessageActionProps) {
	const [showReactions, setShowReactions] = useState(false);

	if (message.isRedacted) return null;

	return (
		<div
			className={cn(
				"absolute -top-4 flex flex-col items-end opacity-0 group-hover:opacity-100 transition-opacity z-10",
				message.isOwn ? "right-2" : "left-10",
			)}
		>
			{showReactions && onReact && (
				<div className="flex items-center gap-0.5 bg-popover border border-border/50 rounded-lg shadow-lg px-1.5 py-1 mb-1">
					{QUICK_REACTIONS.map((emoji) => (
						<button
							key={emoji}
							type="button"
							className={cn(
								"h-8 w-8 flex items-center justify-center text-base rounded hover:scale-125 transition-transform",
								message.myReactions?.[emoji] ? "bg-primary/20" : "hover:bg-muted",
							)}
							title={message.myReactions?.[emoji] ? "Reaktion entfernen" : emoji}
							onClick={() => {
								onReact(message.eventId, emoji, message.myReactions);
								setShowReactions(false);
							}}
						>
							{emoji}
						</button>
					))}
				</div>
			)}

			<div className="flex items-center gap-0.5 bg-popover border border-border/50 rounded-lg shadow-sm px-1 py-0.5">
				{onReact && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Reagieren"
						onClick={() => setShowReactions((v) => !v)}
					>
						<SmilePlus className="h-3.5 w-3.5" />
					</Button>
				)}
				{onReply && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Antworten"
						onClick={() => onReply(message.eventId, message.senderDisplayName, message.body)}
					>
						<Reply className="h-3.5 w-3.5" />
					</Button>
				)}
				{onForward && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Weiterleiten"
						onClick={() => onForward(message.body, message.senderDisplayName)}
					>
						<Share className="h-3.5 w-3.5" />
					</Button>
				)}
				{onThreadOpen && !message.isThreadRoot && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Thread starten"
						onClick={() => onThreadOpen(message.eventId)}
					>
						<MessageSquare className="h-3.5 w-3.5" />
					</Button>
				)}
				{onPin && (
					<Button
						variant="ghost"
						size="icon"
						className={cn("h-7 w-7", isPinned && "text-amber-500")}
						title={isPinned ? "Entpinnen" : "Anpinnen"}
						onClick={() => onPin(message.eventId)}
					>
						{isPinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
					</Button>
				)}
				{onEdit && message.isOwn && message.msgType === "m.text" && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7"
						title="Bearbeiten"
						onClick={() => onEdit(message.eventId, message.body)}
					>
						<Pencil className="h-3.5 w-3.5" />
					</Button>
				)}
				{onRedact && message.isOwn && (
					<Button
						variant="ghost"
						size="icon"
						className="h-7 w-7 hover:bg-destructive/20 hover:text-destructive"
						title="Löschen"
						onClick={() => {
							if (confirm("Nachricht löschen?")) onRedact(message.eventId);
						}}
					>
						<Trash2 className="h-3.5 w-3.5" />
					</Button>
				)}
			</div>
		</div>
	);
}
