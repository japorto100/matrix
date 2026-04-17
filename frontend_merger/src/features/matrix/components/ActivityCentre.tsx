"use client";

import { type NotificationItem, useNotifications } from "@matrix/lib/hooks/useNotifications";
import { AtSign, Bell, MessageSquare, UserPlus, X } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface Props {
	client: MatrixClient;
	onClose: () => void;
	onRoomSelect: (roomId: string) => void;
	onThreadSelect: (roomId: string, threadRootId: string) => void;
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

function NotificationRow({
	item,
	onRoomSelect,
	onThreadSelect,
}: {
	item: NotificationItem;
	onRoomSelect: (roomId: string) => void;
	onThreadSelect: (roomId: string, threadRootId: string) => void;
}) {
	const initials = item.senderName.slice(0, 2).toUpperCase() || "?";
	const icon =
		item.type === "mention" ? (
			<AtSign className="h-3 w-3 text-primary" />
		) : item.type === "thread" ? (
			<MessageSquare className="h-3 w-3 text-blue-400" />
		) : (
			<UserPlus className="h-3 w-3 text-emerald-500" />
		);

	return (
		<button
			type="button"
			className="w-full flex items-start gap-2.5 px-3 py-2 hover:bg-accent/50 transition-colors text-left rounded-md"
			onClick={() => {
				if (item.type === "thread" && item.threadRootId) {
					onThreadSelect(item.roomId, item.threadRootId);
				} else {
					onRoomSelect(item.roomId);
				}
			}}
		>
			<Avatar className="h-7 w-7 shrink-0 mt-0.5">
				{item.senderAvatarUrl && <AvatarImage src={item.senderAvatarUrl} alt={item.senderName} />}
				<AvatarFallback className="text-[10px] font-semibold bg-muted text-muted-foreground">
					{initials}
				</AvatarFallback>
			</Avatar>
			<div className="flex-1 min-w-0">
				<div className="flex items-center gap-1.5">
					{icon}
					<span className="text-xs font-semibold truncate">{item.senderName}</span>
					<span className="text-[10px] text-muted-foreground shrink-0">
						{shortTimeAgo(item.timestamp)}
					</span>
				</div>
				<p className="text-[10px] text-muted-foreground truncate">{item.roomName}</p>
				<p className="text-xs text-muted-foreground/80 truncate mt-0.5">{item.body}</p>
			</div>
		</button>
	);
}

export function ActivityCentre({ client, onClose, onRoomSelect, onThreadSelect }: Props) {
	const { items } = useNotifications(client);

	const mentions = items.filter((i) => i.type === "mention");
	const threads = items.filter((i) => i.type === "thread");
	const invites = items.filter((i) => i.type === "invite");

	return (
		<div className="w-[380px] shrink-0 flex flex-col border-l border-border/50 bg-background overflow-hidden">
			<div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 shrink-0">
				<div className="flex items-center gap-2">
					<Bell className="h-4 w-4" />
					<span className="text-sm font-semibold">Aktivität</span>
					{items.length > 0 && (
						<Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
							{items.length}
						</Badge>
					)}
				</div>
				<Button variant="ghost" size="icon" onClick={onClose} className="shrink-0 h-8 w-8">
					<X className="h-4 w-4" />
				</Button>
			</div>

			<Tabs defaultValue="all" className="flex-1 flex flex-col overflow-hidden">
				<TabsList className="mx-4 mt-2 h-7 bg-muted/30 p-0.5 shrink-0">
					<TabsTrigger value="all" className="text-[10px] h-6 px-2">
						Alle ({items.length})
					</TabsTrigger>
					<TabsTrigger value="mentions" className="text-[10px] h-6 px-2">
						Mentions ({mentions.length})
					</TabsTrigger>
					<TabsTrigger value="threads" className="text-[10px] h-6 px-2">
						Threads ({threads.length})
					</TabsTrigger>
					<TabsTrigger value="invites" className="text-[10px] h-6 px-2">
						Einladungen ({invites.length})
					</TabsTrigger>
				</TabsList>

				<div className="flex-1 overflow-y-auto">
					<TabsContent value="all" className="p-2 space-y-0.5 mt-0">
						{items.length === 0 ? (
							<EmptyState />
						) : (
							items.map((item) => (
								<NotificationRow
									key={item.id}
									item={item}
									onRoomSelect={onRoomSelect}
									onThreadSelect={onThreadSelect}
								/>
							))
						)}
					</TabsContent>
					<TabsContent value="mentions" className="p-2 space-y-0.5 mt-0">
						{mentions.length === 0 ? (
							<EmptyState text="Keine Mentions" />
						) : (
							mentions.map((item) => (
								<NotificationRow
									key={item.id}
									item={item}
									onRoomSelect={onRoomSelect}
									onThreadSelect={onThreadSelect}
								/>
							))
						)}
					</TabsContent>
					<TabsContent value="threads" className="p-2 space-y-0.5 mt-0">
						{threads.length === 0 ? (
							<EmptyState text="Keine Thread-Antworten" />
						) : (
							threads.map((item) => (
								<NotificationRow
									key={item.id}
									item={item}
									onRoomSelect={onRoomSelect}
									onThreadSelect={onThreadSelect}
								/>
							))
						)}
					</TabsContent>
					<TabsContent value="invites" className="p-2 space-y-0.5 mt-0">
						{invites.length === 0 ? (
							<EmptyState text="Keine Einladungen" />
						) : (
							invites.map((item) => (
								<NotificationRow
									key={item.id}
									item={item}
									onRoomSelect={onRoomSelect}
									onThreadSelect={onThreadSelect}
								/>
							))
						)}
					</TabsContent>
				</div>
			</Tabs>
		</div>
	);
}

function EmptyState({ text = "Keine Aktivität" }: { text?: string }) {
	return (
		<div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
			<Bell className="h-8 w-8 mb-2 opacity-40" />
			<p className="text-sm">{text}</p>
		</div>
	);
}
