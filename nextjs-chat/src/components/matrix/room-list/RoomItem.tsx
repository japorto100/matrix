"use client";

import { LogOut, MoreVertical, Star, Trash2 } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { RoomInfo } from "@/lib/matrix/types";
import { hashColor, mxcToHttp } from "@/lib/matrix/utils";
import { cn } from "@/lib/utils";

const AVATAR_COLORS = [
	"bg-blue-500", "bg-emerald-500", "bg-violet-500", "bg-amber-500",
	"bg-rose-500", "bg-cyan-500", "bg-indigo-500", "bg-pink-500",
];
const avatarColor = (name: string) => hashColor(name, AVATAR_COLORS);

function formatLastMessage(msg: string | undefined): string {
	if (!msg) return "";
	if (msg.startsWith("** Unable to decrypt") || msg.includes("DecryptionError")) return "Verschlüsselte Nachricht";
	if (msg.startsWith("* ")) return msg.slice(2);
	return msg;
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

interface Props {
	room: RoomInfo;
	isSelected: boolean;
	onSelect: (roomId: string) => void;
	client?: MatrixClient | null;
}

export function RoomItem({ room, isSelected, onSelect, client }: Props) {
	const initials = room.name.slice(0, 2).toUpperCase();
	const timeAgo = room.lastTimestamp ? shortTimeAgo(room.lastTimestamp) : null;
	const avatarSrc = room.avatarUrl?.startsWith("mxc://") ? mxcToHttp(room.avatarUrl) : room.avatarUrl;
	const lastMsg = formatLastMessage(room.lastMessage);
	const isEncryptedMsg = lastMsg === "Verschlüsselte Nachricht";
	const isDM = !!room.dmUserId;

	const handleLeave = async () => {
		if (!client) return;
		try {
			const matrixRoom = client.getRoom(room.roomId);
			if (matrixRoom?.getMyMembership() !== "join") {
				client.store.removeRoom(room.roomId);
				toast.success(isDM ? "Chat entfernt." : "Raum entfernt.");
				return;
			}
			await client.leave(room.roomId);
			await client.forget(room.roomId).catch(() => {});
			toast.success(isDM ? "Chat gelöscht." : "Raum verlassen.");
		} catch (err) {
			toast.error("Verbindungsfehler.");
			console.error("[RoomList] leave failed:", err);
		}
	};

	const handleToggleFavourite = async () => {
		if (!client) return;
		try {
			if (room.isFavourite) {
				await client.deleteRoomTag(room.roomId, "m.favourite");
			} else {
				await client.setRoomTag(room.roomId, "m.favourite", { order: 0.5 });
			}
			toast.success(room.isFavourite ? "Favorit entfernt." : "Als Favorit markiert.");
		} catch (err) {
			toast.error("Verbindungsfehler.");
			console.error("[RoomList] favourite toggle failed:", err);
		}
	};

	return (
		<div className="relative group">
			<div
				onClick={() => onSelect(room.roomId)}
				className={cn(
					"w-full flex items-center gap-3 px-2.5 py-2.5 rounded-lg text-left transition-colors overflow-hidden cursor-pointer",
					"hover:bg-accent/50",
					isSelected && "bg-accent",
				)}
			>
				<div className="relative shrink-0">
					<Avatar className="h-10 w-10">
						{avatarSrc && <AvatarImage src={avatarSrc} alt={room.name} />}
						<AvatarFallback className={cn("text-xs font-semibold text-white", avatarColor(room.name))}>{initials}</AvatarFallback>
					</Avatar>
					{room.isOnline && <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 border-2 border-sidebar" />}
				</div>

				<div className="flex-1 min-w-0">
					<div className="flex items-center justify-between gap-1.5">
						<span className="flex items-center gap-1 min-w-0">
							{room.isFavourite && <Star className="h-3 w-3 text-amber-500 fill-amber-500 shrink-0" />}
							<span className={cn("text-sm truncate", room.unreadCount > 0 ? "font-semibold" : "font-medium")}>{room.name}</span>
						</span>
						{timeAgo && <span className={cn("text-[10px] shrink-0 group-hover:hidden", room.unreadCount > 0 ? "text-primary font-medium" : "text-muted-foreground")}>{timeAgo}</span>}
						{client && (
							<DropdownMenu>
								<DropdownMenuTrigger asChild>
									<button type="button" className="hidden group-hover:flex shrink-0 h-5 w-5 items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-accent/80" onClick={(e) => e.stopPropagation()}>
										<MoreVertical className="h-3 w-3" />
									</button>
								</DropdownMenuTrigger>
								<DropdownMenuContent align="end" className="min-w-[160px]">
									<DropdownMenuItem onClick={handleToggleFavourite}>
										<Star className={cn("h-3.5 w-3.5 mr-2", room.isFavourite && "text-amber-500 fill-amber-500")} />
										{room.isFavourite ? "Favorit entfernen" : "Favorit"}
									</DropdownMenuItem>
									<DropdownMenuItem className="text-destructive focus:text-destructive" onClick={handleLeave}>
										{isDM ? <Trash2 className="h-3.5 w-3.5 mr-2" /> : <LogOut className="h-3.5 w-3.5 mr-2" />}
										{isDM ? "Chat löschen" : "Raum verlassen"}
									</DropdownMenuItem>
								</DropdownMenuContent>
							</DropdownMenu>
						)}
					</div>
					<div className="flex items-center justify-between gap-1.5 mt-0.5">
						<p className={cn("text-xs truncate", isEncryptedMsg ? "text-muted-foreground/60 italic" : "text-muted-foreground")}>{lastMsg || "\u00A0"}</p>
						{room.unreadCount > 0 && <span className="shrink-0 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold">{room.unreadCount > 99 ? "99+" : room.unreadCount}</span>}
					</div>
				</div>
			</div>
		</div>
	);
}
