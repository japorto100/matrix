"use client";

import type { ResolvedMessage } from "@matrix/lib/types";
import { hashColor } from "@matrix/lib/utils";
import { Lock } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { memo, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PollMessage } from "../PollMessage";
import { ReadByDialog } from "../ReadByDialog";
import { MessageActions } from "./MessageActions";
import { MessageBubble } from "./MessageContent";
import { Reactions, ThreadChip } from "./Reactions";

const SENDER_COLORS = [
	"text-blue-400",
	"text-emerald-400",
	"text-violet-400",
	"text-amber-400",
	"text-rose-400",
	"text-cyan-400",
	"text-indigo-400",
	"text-pink-400",
	"text-teal-400",
	"text-orange-400",
	"text-lime-400",
	"text-fuchsia-400",
];
const senderColor = (sender: string) => hashColor(sender, SENDER_COLORS);

interface Props {
	message: ResolvedMessage;
	isGrouped?: boolean;
	onReact?: (eventId: string, emoji: string, myReactions?: Record<string, string>) => void;
	onReply?: (eventId: string, sender: string, body: string) => void;
	onEdit?: (eventId: string, body: string) => void;
	onRedact?: (eventId: string) => void;
	onForward?: (body: string, senderName: string) => void;
	onPin?: (eventId: string) => void;
	pinnedEventIds?: string[];
	client?: MatrixClient | null;
	roomId?: string | null;
	onThreadOpen?: (eventId: string) => void;
}

function MessageRaw({
	message,
	isGrouped,
	onReact,
	onReply,
	onEdit,
	onRedact,
	onForward,
	onPin,
	pinnedEventIds,
	client,
	roomId,
	onThreadOpen,
}: Props) {
	const [showReadBy, setShowReadBy] = useState(false);
	const initials = message.senderDisplayName.slice(0, 2).toUpperCase();
	const timeStr = new Date(message.timestamp).toLocaleTimeString("de-DE", {
		hour: "2-digit",
		minute: "2-digit",
	});
	const isEmote = message.msgType === "m.emote";
	const isDecryptError =
		message.body.startsWith("** Unable to decrypt") || message.body.includes("DecryptionError");

	return (
		<div
			className={cn(
				"relative flex gap-3 px-4 group hover:bg-accent/20 transition-colors",
				message.isOwn && "flex-row-reverse",
				isGrouped ? "py-0.5" : "py-1.5",
			)}
		>
			<MessageActions
				message={message}
				onReact={onReact}
				onReply={onReply}
				onEdit={onEdit}
				onRedact={onRedact}
				onForward={onForward}
				onPin={onPin}
				onThreadOpen={onThreadOpen}
				isPinned={pinnedEventIds?.includes(message.eventId)}
			/>
			{!isGrouped ? (
				<Avatar className="h-8 w-8 shrink-0 mt-0.5">
					{message.avatarUrl && (
						<AvatarImage src={message.avatarUrl} alt={message.senderDisplayName} />
					)}
					<AvatarFallback
						className={cn(
							"text-xs font-semibold text-white",
							message.isBot ? "bg-primary/20 text-primary" : "bg-violet-600",
						)}
					>
						{message.isBot ? "AI" : initials}
					</AvatarFallback>
				</Avatar>
			) : (
				<div className="w-8 shrink-0" />
			)}

			<div className={cn("flex flex-col", message.isOwn ? "items-end max-w-[75%]" : "max-w-[75%]")}>
				{!isGrouped && !isEmote && (
					<div className="flex items-baseline gap-2 mb-0.5">
						<span
							className={cn(
								"text-sm font-semibold leading-none",
								message.isOwn ? "text-foreground" : senderColor(message.sender),
							)}
						>
							{message.senderDisplayName}
						</span>
						{message.isBot && (
							<Badge variant="secondary" className="text-[10px] px-1 py-0 h-4">
								Agent
							</Badge>
						)}
						<span className="text-[10px] text-muted-foreground">{timeStr}</span>
						{message.isEdited && (
							<span className="text-[10px] text-muted-foreground italic">(bearbeitet)</span>
						)}
					</div>
				)}

				{isDecryptError ? (
					<div className="flex items-center gap-2 px-3 py-2 rounded-2xl bg-muted/30 border border-border/50 text-muted-foreground italic text-sm">
						<Lock className="h-4 w-4 shrink-0 text-muted-foreground/60" />
						<span>Diese Nachricht kann nicht entschlüsselt werden</span>
					</div>
				) : message.isPoll && message.pollEventId && client && roomId ? (
					<PollMessage
						pollEventId={message.pollEventId}
						roomId={roomId}
						client={client}
						isOwn={message.isOwn}
					/>
				) : (
					<MessageBubble message={message} />
				)}

				{message.isThreadRoot &&
					message.threadReplyCount !== undefined &&
					message.threadReplyCount > 0 &&
					onThreadOpen && (
						<ThreadChip
							count={message.threadReplyCount}
							onOpen={() => onThreadOpen(message.eventId)}
							isOwn={message.isOwn}
						/>
					)}

				{message.reactions && Object.keys(message.reactions).length > 0 && (
					<Reactions
						reactions={message.reactions}
						myReactions={message.myReactions}
						onReact={onReact}
						eventId={message.eventId}
					/>
				)}

				{message.isOwn && message.readBy && message.readBy.length > 0 && (
					<>
						<button
							type="button"
							className="flex items-center gap-0.5 mt-0.5 bg-transparent border-0 p-0 cursor-pointer hover:opacity-80 transition-opacity"
							onClick={() => setShowReadBy(true)}
							title="Gelesen von…"
						>
							{message.readBy.slice(0, 5).map((userId) => {
								const ini = userId.split(":")[0]?.replace("@", "").slice(0, 2).toUpperCase() ?? "?";
								return (
									<span
										key={userId}
										className="inline-flex items-center justify-center h-3.5 w-3.5 rounded-full bg-primary/30 text-primary text-[8px] font-semibold"
									>
										{ini}
									</span>
								);
							})}
							{message.readBy.length > 5 && (
								<span className="text-[8px] text-muted-foreground ml-0.5">
									+{message.readBy.length - 5}
								</span>
							)}
						</button>
						{showReadBy && (
							<ReadByDialog
								open={showReadBy}
								onOpenChange={setShowReadBy}
								readBy={message.readBy}
							/>
						)}
					</>
				)}
			</div>
		</div>
	);
}

export const Message = memo(MessageRaw) as typeof MessageRaw;
