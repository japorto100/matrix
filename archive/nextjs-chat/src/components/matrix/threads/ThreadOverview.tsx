"use client";

import { MessageSquare, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useMemo } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { mxcToHttp } from "@/lib/matrix/utils";

interface Props {
	client: MatrixClient;
	roomId: string;
	onClose: () => void;
	onThreadSelect: (threadRootId: string) => void;
}

function shortTimeAgo(ts: number): string {
	const diff = Date.now() - ts;
	const mins = Math.floor(diff / 60000);
	if (mins < 1) return "jetzt";
	if (mins < 60) return `${mins}m`;
	const hours = Math.floor(mins / 60);
	if (hours < 24) return `${hours}h`;
	const days = Math.floor(hours / 24);
	if (days < 7) return `${days}d`;
	return `${Math.floor(days / 7)}w`;
}

export function ThreadOverview({ client, roomId, onClose, onThreadSelect }: Props) {
	const threads = useMemo(() => {
		const room = client.getRoom(roomId);
		if (!room) return [];
		const threadRoots = room.getThreads();
		return threadRoots
			.map((thread) => {
				const rootEvent = thread.rootEvent;
				if (!rootEvent) return null;
				const sender = rootEvent.getSender() ?? "";
				const senderName = sender.split(":")[0]?.replace("@", "") ?? sender;
				const senderMember = room.getMember(sender);
				const senderAvatar = senderMember?.getMxcAvatarUrl();
				const body = (rootEvent.getContent()?.body as string) ?? "";
				const lastReply = thread.events[thread.events.length - 1];
				const lastReplySender = lastReply?.getSender() ?? "";
				const lastReplySenderName = lastReplySender.split(":")[0]?.replace("@", "") ?? "";
				const lastReplyMember = lastReplySender ? room.getMember(lastReplySender) : null;
				const lastReplyAvatar = lastReplyMember?.getMxcAvatarUrl();
				const lastReplyBody = (lastReply?.getContent()?.body as string) ?? "";
				return {
					rootId: rootEvent.getId() ?? "",
					senderName,
					senderInitials: senderName.slice(0, 2).toUpperCase() || "?",
					senderAvatarUrl: senderAvatar?.startsWith("mxc://") ? mxcToHttp(senderAvatar) : undefined,
					body: body.slice(0, 80),
					replyCount: thread.length,
					lastActivity: lastReply?.getTs() ?? rootEvent.getTs(),
					lastReplySenderName,
					lastReplyInitials: lastReplySenderName.slice(0, 2).toUpperCase() || "?",
					lastReplyAvatarUrl: lastReplyAvatar?.startsWith("mxc://")
						? mxcToHttp(lastReplyAvatar)
						: undefined,
					lastReplyBody: lastReplyBody.slice(0, 60),
				};
			})
			.filter(Boolean)
			.sort((a, b) => b!.lastActivity - a!.lastActivity);
	}, [client, roomId]);

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border/50 bg-background overflow-hidden">
			<div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 shrink-0">
				<div className="flex items-center gap-2">
					<MessageSquare className="h-4 w-4" />
					<span className="text-sm font-semibold">Threads</span>
				</div>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			<div className="flex-1 overflow-y-auto">
				{threads.length === 0 ? (
					<div className="flex flex-col items-center justify-center h-full text-muted-foreground px-4 text-center">
						<MessageSquare className="h-8 w-8 mb-2 opacity-40" />
						<p className="text-sm">Keine Threads in diesem Raum</p>
						<p className="text-xs mt-1">
							Starte einen Thread indem du auf das Thread-Icon bei einer Nachricht klickst.
						</p>
					</div>
				) : (
					<div className="p-2 space-y-0.5">
						{threads.map((thread) => {
							if (!thread) return null;
							return (
								<button
									key={thread.rootId}
									type="button"
									className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-accent/50 transition-colors"
									onClick={() => onThreadSelect(thread.rootId)}
								>
									{/* Thread-Starter */}
									<div className="flex items-center gap-2 mb-1">
										<Avatar className="h-5 w-5 shrink-0">
											{thread.senderAvatarUrl && (
												<AvatarImage src={thread.senderAvatarUrl} alt={thread.senderName} />
											)}
											<AvatarFallback className="text-[8px] font-semibold bg-muted text-muted-foreground">
												{thread.senderInitials}
											</AvatarFallback>
										</Avatar>
										<span className="text-xs font-semibold truncate flex-1">
											{thread.senderName}
										</span>
										<span className="text-[10px] text-muted-foreground shrink-0">
											{shortTimeAgo(thread.lastActivity)}
										</span>
									</div>
									<p className="text-xs text-muted-foreground truncate pl-7">{thread.body}</p>
									{/* Letzte Antwort */}
									<div className="flex items-center gap-2 mt-1.5 pl-7">
										<span className="text-[10px] text-primary font-medium shrink-0">
											{thread.replyCount} {thread.replyCount === 1 ? "Antwort" : "Antworten"}
										</span>
										{thread.lastReplySenderName && (
											<div className="flex items-center gap-1 min-w-0">
												<Avatar className="h-3.5 w-3.5 shrink-0">
													{thread.lastReplyAvatarUrl && (
														<AvatarImage
															src={thread.lastReplyAvatarUrl}
															alt={thread.lastReplySenderName}
														/>
													)}
													<AvatarFallback className="text-[6px] font-semibold bg-muted text-muted-foreground">
														{thread.lastReplyInitials}
													</AvatarFallback>
												</Avatar>
												<span className="text-[10px] text-muted-foreground truncate">
													{thread.lastReplySenderName}: {thread.lastReplyBody}
												</span>
											</div>
										)}
									</div>
								</button>
							);
						})}
					</div>
				)}
			</div>
		</div>
	);
}
