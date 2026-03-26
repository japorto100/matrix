"use client";

import { formatDistanceToNow } from "date-fns";
import { de } from "date-fns/locale";
import { MessageSquarePlus, Plus } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { memo } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import type { SpaceInfo } from "@/lib/matrix/hooks/useSpaces";
import type { RoomInfo } from "@/lib/matrix/types";
import { cn } from "@/lib/utils";
import { CreateDMDialog } from "./CreateDMDialog";
import { CreateRoomDialog } from "./CreateRoomDialog";
import { SpaceSelector } from "./SpaceSelector";
import { UserProfileDialog } from "./UserProfileDialog";

interface Props {
	rooms: RoomInfo[];
	selectedRoomId: string | null;
	onSelect: (roomId: string) => void;
	isLoading?: boolean;
	client?: MatrixClient | null;
	spaces?: SpaceInfo[];
	selectedSpaceId?: string | null;
	onSpaceSelect?: (spaceId: string | null) => void;
}

function RoomListRaw({
	rooms,
	selectedRoomId,
	onSelect,
	isLoading,
	client,
	spaces,
	selectedSpaceId,
	onSpaceSelect,
}: Props) {
	if (isLoading) {
		return (
			<aside className="w-64 border-r flex flex-col bg-sidebar">
				<div className="p-3 border-b">
					<h1 className="font-semibold text-sm">Matrix Chat</h1>
				</div>
				<div className="p-2 space-y-1">
					{["sk-1", "sk-2", "sk-3", "sk-4", "sk-5"].map((key) => (
						<div key={key} className="flex items-center gap-2 p-2">
							<Skeleton className="h-8 w-8 rounded-full" />
							<div className="flex-1 space-y-1">
								<Skeleton className="h-3 w-24" />
								<Skeleton className="h-3 w-32" />
							</div>
						</div>
					))}
				</div>
			</aside>
		);
	}

	// F-1: Space-Filterung
	const selectedSpace = spaces?.find((s) => s.roomId === selectedSpaceId);
	const filteredRooms = selectedSpace
		? rooms.filter((r) => selectedSpace.childRoomIds.includes(r.roomId))
		: rooms;

	// UI-7: Eigenes Profil für Footer
	const myUserId = client?.getUserId() ?? null;
	const myUser = myUserId ? client?.getUser(myUserId) : null;
	const myDisplayName = myUser?.displayName ?? myUserId ?? "";
	const myInitials = myDisplayName.slice(0, 2).toUpperCase() || "?";
	const myAvatarUrl = myUser?.avatarUrl?.startsWith("mxc://")
		? `/api/matrix/media?mxc=${encodeURIComponent(myUser.avatarUrl.slice(6))}`
		: undefined;

	return (
		<aside className="w-64 border-r flex flex-col bg-sidebar shrink-0">
			<div className="p-3 border-b">
				<div className="flex items-center justify-between">
					<h1 className="font-semibold text-sm">Matrix Chat</h1>
					{client && (
						<div className="flex items-center gap-0.5">
							<CreateRoomDialog
								client={client}
								trigger={
									<Button variant="ghost" size="icon" className="h-6 w-6" title="Raum erstellen">
										<Plus className="h-3.5 w-3.5" />
									</Button>
								}
							/>
							<CreateDMDialog
								client={client}
								trigger={
									<Button variant="ghost" size="icon" className="h-6 w-6" title="Direktnachricht">
										<MessageSquarePlus className="h-3.5 w-3.5" />
									</Button>
								}
							/>
						</div>
					)}
				</div>
				<p className="text-[10px] text-muted-foreground mt-0.5">{filteredRooms.length} Räume</p>
			</div>
			{/* F-1: Space-Auswahl */}
			{spaces && spaces.length > 0 && onSpaceSelect && (
				<SpaceSelector
					spaces={spaces}
					selectedSpaceId={selectedSpaceId ?? null}
					onSelect={onSpaceSelect}
				/>
			)}
			<ScrollArea className="flex-1">
				<div className="p-2 space-y-0.5">
					{filteredRooms.map((room) => (
						<RoomItem
							key={room.roomId}
							room={room}
							isSelected={room.roomId === selectedRoomId}
							onSelect={onSelect}
						/>
					))}
					{filteredRooms.length === 0 && (
						<p className="text-xs text-muted-foreground text-center py-8 px-4">
							Keine Räume gefunden.
						</p>
					)}
				</div>
			</ScrollArea>
			{/* UI-7: Eigenes Profil Footer */}
			{client && (
				<div className="border-t p-2 flex items-center gap-2">
					<UserProfileDialog
						client={client}
						trigger={
							<button
								type="button"
								className="flex items-center gap-2 w-full px-2 py-1.5 rounded-md hover:bg-accent transition-colors text-left"
							>
								<Avatar className="h-7 w-7">
									{myAvatarUrl && <AvatarImage src={myAvatarUrl} />}
									<AvatarFallback className="text-[10px]">{myInitials}</AvatarFallback>
								</Avatar>
								<span className="text-xs font-medium truncate">{myDisplayName}</span>
							</button>
						}
					/>
				</div>
			)}
		</aside>
	);
}

interface RoomItemProps {
	room: RoomInfo;
	isSelected: boolean;
	onSelect: (roomId: string) => void;
}

function RoomItem({ room, isSelected, onSelect }: RoomItemProps) {
	const initials = room.name.slice(0, 2).toUpperCase();
	const timeAgo = room.lastTimestamp
		? formatDistanceToNow(room.lastTimestamp, { addSuffix: false, locale: de })
		: null;
	const avatarSrc = room.avatarUrl?.startsWith("mxc://")
		? `/api/matrix/media?mxc=${encodeURIComponent(room.avatarUrl.slice(6))}`
		: room.avatarUrl;

	return (
		<button
			type="button"
			onClick={() => onSelect(room.roomId)}
			className={cn(
				"w-full flex items-center gap-2.5 px-2 py-2 rounded-md text-left transition-colors",
				"hover:bg-accent hover:text-accent-foreground",
				isSelected && "bg-accent text-accent-foreground",
			)}
		>
			<div className="relative shrink-0">
				<Avatar className="h-8 w-8">
					{avatarSrc && <AvatarImage src={avatarSrc} alt={room.name} />}
					<AvatarFallback className="text-xs font-semibold bg-muted">{initials}</AvatarFallback>
				</Avatar>
				{room.isOnline && (
					<span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-green-500 border-2 border-sidebar" />
				)}
			</div>
			<div className="flex-1 min-w-0">
				<div className="flex items-center justify-between gap-1">
					<span className="text-sm font-medium truncate">{room.name}</span>
					<div className="flex items-center gap-1 shrink-0">
						{room.unreadCount > 0 && (
							<Badge variant="destructive" className="text-[9px] px-1 py-0 h-4 min-w-[16px]">
								{room.unreadCount > 99 ? "99+" : room.unreadCount}
							</Badge>
						)}
						{timeAgo && <span className="text-[10px] text-muted-foreground">{timeAgo}</span>}
					</div>
				</div>
				{room.lastMessage && (
					<p className="text-[11px] text-muted-foreground truncate mt-0.5">{room.lastMessage}</p>
				)}
			</div>
		</button>
	);
}

export const RoomList = memo(RoomListRaw);
