"use client";

import { LayoutGrid } from "lucide-react";
import type { ResolvedMessage } from "@/lib/matrix/types";
import { cn } from "@/lib/utils";
import {
	AudioContent,
	EmoteContent,
	FileContent,
	ImageContent,
	LocationContent,
	NoticeContent,
	StickerContent,
	TextContent,
	VideoContent,
} from "./content";

export { TextContent } from "./content";

export function ReplyBanner({ replyTo }: { replyTo: NonNullable<ResolvedMessage["replyTo"]> }) {
	return (
		<div className="flex flex-col gap-0.5 mb-2 pl-2.5 border-l-2 border-blue-400/50 max-w-full">
			<span className="text-sm font-semibold text-blue-400">{replyTo.sender}</span>
			<span className="text-sm text-muted-foreground line-clamp-2">{replyTo.body}</span>
		</div>
	);
}

export function MessageBubble({ message }: { message: ResolvedMessage }) {
	if (message.msgType === "m.sticker") return <StickerContent message={message} />;
	if (message.msgType === "m.emote") return <EmoteContent message={message} />;

	return (
		<div
			className={cn(
				"inline-block rounded-2xl px-3 py-2 text-sm",
				message.isOwn
					? "bg-zinc-800/90 text-white rounded-tr-sm"
					: message.msgType === "m.notice"
						? "bg-muted/40 rounded-tl-sm border border-border"
						: message.isMentioned
							? "bg-yellow-500/15 rounded-tl-sm border border-yellow-500/40"
							: "bg-muted rounded-tl-sm",
			)}
		>
			{message.replyTo && <ReplyBanner replyTo={message.replyTo} />}
			{(() => {
				switch (message.msgType) {
					case "m.image": return <ImageContent message={message} />;
					case "m.video": return <VideoContent message={message} />;
					case "m.audio": return <AudioContent message={message} />;
					case "m.file": return <FileContent message={message} />;
					case "m.location": return <LocationContent message={message} />;
					case "m.notice": return <NoticeContent message={message} />;
					case "m.widget": return (
						<div className="flex items-center gap-2 text-xs text-muted-foreground italic">
							<LayoutGrid className="h-4 w-4 shrink-0" /><span>{message.body}</span>
						</div>
					);
					default: return <TextContent message={message} />;
				}
			})()}
		</div>
	);
}
