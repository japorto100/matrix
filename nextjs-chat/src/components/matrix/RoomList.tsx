"use client";

import { LogOut, MessageSquarePlus, MoreVertical, Plus, Search, Star, Trash2 } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { memo, useMemo, useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { SpaceInfo } from "@/lib/matrix/hooks/useSpaces";
import type { RoomInfo } from "@/lib/matrix/types";
import { cn } from "@/lib/utils";
import { CreateDMDialog } from "./CreateDMDialog";
import { CreateRoomDialog } from "./CreateRoomDialog";

// Hash-basierte Farbe für Avatare ohne Bild
const AVATAR_COLORS = [
	"bg-blue-500",
	"bg-emerald-500",
	"bg-violet-500",
	"bg-amber-500",
	"bg-rose-500",
	"bg-cyan-500",
	"bg-indigo-500",
	"bg-pink-500",
];
function avatarColor(name: string): string {
	let hash = 0;
	for (let i = 0; i < name.length; i++) hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
	return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length] ?? "bg-blue-600";
}

type Filter = "all" | "unread" | "people" | "rooms" | "favourites";

interface Props {
	rooms: RoomInfo[];
	selectedRoomId: string | null;
	onSelect: (roomId: string) => void;
	isLoading?: boolean;
	client?: MatrixClient | null;
	spaces?: SpaceInfo[];
	selectedSpaceId?: string | null;
}

function RoomListRaw({
	rooms,
	selectedRoomId,
	onSelect,
	isLoading,
	client,
	spaces,
	selectedSpaceId,
}: Props) {
	const [search, setSearch] = useState("");
	const [filter, setFilter] = useState<Filter>("all");

	// Space-Filterung
	const selectedSpace = spaces?.find((s) => s.roomId === selectedSpaceId);
	const filteredRooms = useMemo(() => {
		let list = selectedSpace
			? rooms.filter((r) => selectedSpace.childRoomIds.includes(r.roomId))
			: rooms;

		// Tab-Filter
		if (filter === "unread") list = list.filter((r) => r.unreadCount > 0);
		if (filter === "people") list = list.filter((r) => r.otherUserId);
		if (filter === "rooms") list = list.filter((r) => !r.otherUserId);
		if (filter === "favourites") list = list.filter((r) => r.isFavourite);

		// Suchfilter
		if (search.trim()) {
			const q = search.toLowerCase();
			list = list.filter((r) => r.name.toLowerCase().includes(q));
		}

		return list;
	}, [rooms, selectedSpace, filter, search]);

	const totalUnread = rooms.reduce((sum, r) => sum + r.unreadCount, 0);

	if (isLoading) {
		return (
			<aside className="w-72 border-r border-border/50 flex flex-col bg-sidebar shrink-0 overflow-hidden">
				<div className="p-3 border-b border-border/50">
					<div className="h-9 rounded-lg bg-muted/30 animate-pulse" />
				</div>
				<div className="p-2 space-y-1">
					{Array.from({ length: 6 }, (_, i) => (
						// biome-ignore lint/suspicious/noArrayIndexKey: Statische Skeleton-Elemente, werden nie umgeordnet
						<div key={i} className="flex items-center gap-3 p-2.5">
							<Skeleton className="h-10 w-10 rounded-full" />
							<div className="flex-1 space-y-2">
								<Skeleton className="h-3.5 w-28" />
								<Skeleton className="h-3 w-36" />
							</div>
						</div>
					))}
				</div>
			</aside>
		);
	}

	return (
		<aside className="w-72 border-r border-border/50 flex flex-col bg-sidebar shrink-0 overflow-hidden">
			{/* Header */}
			<div className="p-3 space-y-2.5">
				<div className="flex items-center justify-between">
					<h1 className="font-semibold text-base">Chats</h1>
					{client && (
						<div className="flex items-center gap-0.5">
							<CreateRoomDialog
								client={client}
								trigger={
									<Button variant="ghost" size="icon" className="h-7 w-7" title="Raum erstellen">
										<Plus className="h-4 w-4" />
									</Button>
								}
							/>
							<CreateDMDialog
								client={client}
								trigger={
									<Button variant="ghost" size="icon" className="h-7 w-7" title="Direktnachricht">
										<MessageSquarePlus className="h-4 w-4" />
									</Button>
								}
							/>
						</div>
					)}
				</div>
				{/* Suchleiste */}
				<div className="relative">
					<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
					<input
						type="text"
						placeholder="Suchen..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg bg-muted/30 border border-border/50 placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
					/>
				</div>
				{/* Filter-Tabs */}
				<div className="flex gap-1 flex-wrap">
					{(
						[
							["all", "Alle"],
							["unread", `Ungelesen${totalUnread > 0 ? ` (${totalUnread})` : ""}`],
							["favourites", "Favoriten"],
							["people", "Personen"],
							["rooms", "Räume"],
						] as [Filter, string][]
					).map(([key, label]) => (
						<button
							key={key}
							type="button"
							onClick={() => setFilter(key)}
							className={cn(
								"px-2.5 py-1 text-xs rounded-full transition-colors",
								filter === key
									? "bg-primary text-primary-foreground"
									: "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
							)}
						>
							{label}
						</button>
					))}
				</div>
			</div>

			{/* Room-Liste */}
			<div className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide">
				<div className="px-2 pb-2 space-y-0.5">
					{filteredRooms.map((room) => (
						<RoomItem
							key={room.roomId}
							room={room}
							isSelected={room.roomId === selectedRoomId}
							onSelect={onSelect}
							client={client}
						/>
					))}
					{filteredRooms.length === 0 && (
						<p className="text-xs text-muted-foreground text-center py-8 px-4">
							{search
								? "Keine Ergebnisse."
								: filter === "unread"
									? "Keine ungelesenen Nachrichten."
									: filter === "favourites"
										? "Keine Favoriten."
										: filter === "people"
											? "Keine Direktnachrichten."
											: filter === "rooms"
												? "Keine Räume."
												: "Keine Chats."}
						</p>
					)}
				</div>
			</div>
		</aside>
	);
}

interface RoomItemProps {
	room: RoomInfo;
	isSelected: boolean;
	onSelect: (roomId: string) => void;
	client?: MatrixClient | null;
}

function formatLastMessage(msg: string | undefined): string {
	if (!msg) return "";
	// DecryptionError graceful anzeigen
	if (msg.startsWith("** Unable to decrypt") || msg.includes("DecryptionError")) {
		return "Verschlüsselte Nachricht";
	}
	// Edit-Prefix entfernen (Matrix-Spec: "* " vor editiertem Body)
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
	const weeks = Math.floor(days / 7);
	return `${weeks}w`;
}

function RoomItem({ room, isSelected, onSelect, client }: RoomItemProps) {
	const [showMenu, setShowMenu] = useState(false);
	const [menuPos, setMenuPos] = useState({ x: 0, y: 0 });
	const initials = room.name.slice(0, 2).toUpperCase();
	const timeAgo = room.lastTimestamp ? shortTimeAgo(room.lastTimestamp) : null;
	const avatarSrc = room.avatarUrl?.startsWith("mxc://")
		? `/api/matrix/media?mxc=${encodeURIComponent(room.avatarUrl.slice(6))}`
		: room.avatarUrl;
	const lastMsg = formatLastMessage(room.lastMessage);
	const isEncryptedMsg = lastMsg === "Verschlüsselte Nachricht";
	const isDM = !!room.otherUserId;

	const handleLeave = async () => {
		if (!client) return;
		setShowMenu(false);
		try {
			// Prüfe ob wir joined sind
			const matrixRoom = client.getRoom(room.roomId);
			const membership = matrixRoom?.getMyMembership();
			if (membership !== "join") {
				// Nicht joined — nur aus Store entfernen
				client.store.removeRoom(room.roomId);
				toast.success(isDM ? "Chat entfernt." : "Raum entfernt.");
				return;
			}
			const token = client.getAccessToken();
			const base = client.baseUrl;
			const rid = encodeURIComponent(room.roomId);
			// 1. Leave
			const leaveRes = await fetch(`${base}/_matrix/client/v3/rooms/${rid}/leave`, {
				method: "POST",
				headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
				body: "{}",
			});
			if (!leaveRes.ok) {
				toast.error("Verlassen fehlgeschlagen.");
				return;
			}
			// 2. Forget
			await fetch(`${base}/_matrix/client/v3/rooms/${rid}/forget`, {
				method: "POST",
				headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
				body: "{}",
			}).catch(() => {});
			// 3. Aus SDK Store entfernen + Event emittern
			client.store.removeRoom(room.roomId);
			client.emit("deleteRoom" as any, room.roomId);
			toast.success(isDM ? "Chat gelöscht." : "Raum verlassen.");
		} catch (err) {
			toast.error("Verbindungsfehler.");
			console.error("[RoomList] leave failed:", err);
		}
	};

	const handleToggleFavourite = async () => {
		if (!client) return;
		setShowMenu(false);
		try {
			const token = client.getAccessToken();
			const base = client.baseUrl;
			const uid = encodeURIComponent(client.getUserId() ?? "");
			const rid = encodeURIComponent(room.roomId);
			const method = room.isFavourite ? "DELETE" : "PUT";
			const res = await fetch(
				`${base}/_matrix/client/v3/user/${uid}/rooms/${rid}/tags/m.favourite`,
				{
					method,
					headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
					...(method === "PUT" ? { body: JSON.stringify({ order: 0.5 }) } : {}),
				},
			);
			if (res.ok) {
				// SDK-Store sofort updaten damit UI reagiert
				const matrixRoom = client.getRoom(room.roomId);
				if (matrixRoom) {
					if (room.isFavourite) {
						delete matrixRoom.tags["m.favourite"];
					} else {
						matrixRoom.tags["m.favourite"] = { order: 0.5 };
					}
					matrixRoom.emit("Room.tags" as any, matrixRoom);
				}
				toast.success(room.isFavourite ? "Favorit entfernt." : "Als Favorit markiert.");
			} else {
				toast.error("Favorit konnte nicht gesetzt werden.");
			}
		} catch (err) {
			toast.error("Verbindungsfehler.");
			console.error("[RoomList] favourite toggle failed:", err);
		}
	};

	return (
		<div className="relative group">
			{/* biome-ignore lint/a11y/useKeyWithClickEvents: Room selection via click */}
			<div
				onClick={() => onSelect(room.roomId)}
				className={cn(
					"w-full flex items-center gap-3 px-2.5 py-2.5 rounded-lg text-left transition-colors overflow-hidden cursor-pointer",
					"hover:bg-accent/50",
					isSelected && "bg-accent",
				)}
			>
				{/* Avatar */}
				<div className="relative shrink-0">
					<Avatar className="h-10 w-10">
						{avatarSrc && <AvatarImage src={avatarSrc} alt={room.name} />}
						<AvatarFallback
							className={cn("text-xs font-semibold text-white", avatarColor(room.name))}
						>
							{initials}
						</AvatarFallback>
					</Avatar>
					{room.isOnline && (
						<span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 border-2 border-sidebar" />
					)}
				</div>

				{/* Content */}
				<div className="flex-1 min-w-0">
					<div className="flex items-center justify-between gap-1.5">
						<span className="flex items-center gap-1 min-w-0">
							{room.isFavourite && (
								<Star className="h-3 w-3 text-amber-500 fill-amber-500 shrink-0" />
							)}
							<span
								className={cn(
									"text-sm truncate",
									room.unreadCount > 0 ? "font-semibold" : "font-medium",
								)}
							>
								{room.name}
							</span>
						</span>
						{timeAgo && (
							<span
								className={cn(
									"text-[10px] shrink-0 group-hover:hidden",
									room.unreadCount > 0 ? "text-primary font-medium" : "text-muted-foreground",
								)}
							>
								{timeAgo}
							</span>
						)}
						{client && (
							<button
								type="button"
								className="hidden group-hover:flex shrink-0 h-5 w-5 items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-accent/80"
								onClick={(e) => {
									e.stopPropagation();
									const rect = e.currentTarget.getBoundingClientRect();
									setMenuPos({ x: rect.left, y: rect.bottom + 4 });
									setShowMenu(true);
								}}
							>
								<MoreVertical className="h-3 w-3" />
							</button>
						)}
					</div>
					<div className="flex items-center justify-between gap-1.5 mt-0.5">
						<p
							className={cn(
								"text-xs truncate",
								isEncryptedMsg ? "text-muted-foreground/60 italic" : "text-muted-foreground",
							)}
						>
							{lastMsg || "\u00A0"}
						</p>
						{room.unreadCount > 0 && (
							<span className="shrink-0 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold">
								{room.unreadCount > 99 ? "99+" : room.unreadCount}
							</span>
						)}
					</div>
				</div>
			</div>

			{/* Kontextmenü */}
			{showMenu && (
				<>
					{/* biome-ignore lint/a11y/useKeyWithClickEvents: Overlay zum Schließen */}
					<div className="fixed inset-0 z-40" onMouseDown={() => setShowMenu(false)} />
					<div
						className="fixed z-50 bg-popover border border-border rounded-lg shadow-lg py-1 min-w-[160px]"
						style={{ left: menuPos.x, top: menuPos.y }}
					>
						<button
							type="button"
							className="w-full flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent/50 transition-colors"
							onClick={handleToggleFavourite}
						>
							<Star
								className={cn("h-3.5 w-3.5", room.isFavourite && "text-amber-500 fill-amber-500")}
							/>
							{room.isFavourite ? "Favorit entfernen" : "Favorit"}
						</button>
						<button
							type="button"
							className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
							onClick={handleLeave}
						>
							{isDM ? <Trash2 className="h-3.5 w-3.5" /> : <LogOut className="h-3.5 w-3.5" />}
							{isDM ? "Chat löschen" : "Raum verlassen"}
						</button>
					</div>
				</>
			)}
		</div>
	);
}

export const RoomList = memo(RoomListRaw);
