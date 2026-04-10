"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import { MessageSquarePlus, Plus, Search } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { memo, useCallback, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { SpaceInfo } from "@/lib/matrix/hooks/useSpaces";
import type { RoomInfo } from "@/lib/matrix/types";
import { CreateRoomDialog } from "../CreateRoomDialog";
import { CreateDMDialog } from "../contacts/CreateDMDialog";
import { InviteItem } from "./InviteItem";
import { RoomItem } from "./RoomItem";

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

	const selectedSpace = spaces?.find((s) => s.roomId === selectedSpaceId);
	const { inviteRooms, filteredRooms } = useMemo(() => {
		let list = selectedSpace
			? rooms.filter((r) => selectedSpace.childRoomIds.includes(r.roomId))
			: rooms;
		const invites = filter === "all" ? list.filter((r) => r.membership === "invite") : [];
		list = list.filter((r) => r.membership === "join");
		if (filter === "unread") list = list.filter((r) => r.unreadCount > 0);
		if (filter === "people") list = list.filter((r) => r.dmUserId);
		if (filter === "rooms") list = list.filter((r) => !r.dmUserId);
		if (filter === "favourites") list = list.filter((r) => r.isFavourite);
		if (search.trim()) {
			const q = search.toLowerCase();
			list = list.filter((r) => r.name.toLowerCase().includes(q));
		}
		return { inviteRooms: invites, filteredRooms: list };
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
						// biome-ignore lint/suspicious/noArrayIndexKey: static skeletons
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
			<div className="p-3 space-y-2.5">
				<div className="flex items-center justify-between">
					<h1 className="font-semibold text-base">Chats</h1>
					{client && (
						<div className="flex items-center gap-0.5">
							<CreateRoomDialog
								client={client}
								spaceId={selectedSpaceId}
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

				<div className="relative">
					<Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
					<Input
						placeholder="Suchen..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="pl-8 h-8 text-sm"
					/>
				</div>

				<Tabs value={filter} onValueChange={(v) => setFilter(v as Filter)} className="w-full">
					<TabsList className="h-7 w-full bg-muted/30 p-0.5">
						<TabsTrigger value="all" className="text-[10px] h-6 px-2">
							Alle
						</TabsTrigger>
						<TabsTrigger value="unread" className="text-[10px] h-6 px-2">
							Ungelesen{totalUnread > 0 ? ` (${totalUnread})` : ""}
						</TabsTrigger>
						<TabsTrigger value="favourites" className="text-[10px] h-6 px-2">
							Favoriten
						</TabsTrigger>
						<TabsTrigger value="people" className="text-[10px] h-6 px-2">
							Personen
						</TabsTrigger>
						<TabsTrigger value="rooms" className="text-[10px] h-6 px-2">
							Räume
						</TabsTrigger>
					</TabsList>
				</Tabs>
			</div>

			<VirtualizedRoomList
				inviteRooms={inviteRooms}
				filteredRooms={filteredRooms}
				selectedRoomId={selectedRoomId}
				onSelect={onSelect}
				client={client}
				search={search}
				filter={filter}
			/>
		</aside>
	);
}

function VirtualizedRoomList({
	inviteRooms,
	filteredRooms,
	selectedRoomId,
	onSelect,
	client,
	search,
	filter,
}: {
	inviteRooms: RoomInfo[];
	filteredRooms: RoomInfo[];
	selectedRoomId: string | null;
	onSelect: (roomId: string) => void;
	client?: MatrixClient | null;
	search: string;
	filter: string;
}) {
	const scrollRef = useRef<HTMLDivElement>(null);
	const [inviteListRef] = useAutoAnimate<HTMLDivElement>();
	const virtualizer = useVirtualizer({
		count: filteredRooms.length,
		getScrollElement: () => scrollRef.current,
		estimateSize: () => 60,
		overscan: 5,
	});

	// Pfeiltasten-Navigation in der RoomList
	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
			e.preventDefault();
			const currentIdx = filteredRooms.findIndex((r) => r.roomId === selectedRoomId);
			const nextIdx =
				e.key === "ArrowDown"
					? Math.min(currentIdx + 1, filteredRooms.length - 1)
					: Math.max(currentIdx - 1, 0);
			const nextRoom = filteredRooms[nextIdx];
			if (nextRoom) {
				onSelect(nextRoom.roomId);
				virtualizer.scrollToIndex(nextIdx, { align: "auto" });
			}
		},
		[filteredRooms, selectedRoomId, onSelect, virtualizer],
	);

	return (
		<div
			ref={scrollRef}
			className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide"
			onKeyDown={handleKeyDown}
			tabIndex={0}
		>
			<div className="px-2 pb-2">
				{inviteRooms.length > 0 && (
					<div className="mb-2" ref={inviteListRef}>
						<p className="text-[10px] font-semibold text-primary uppercase tracking-wider px-2.5 py-1">
							Einladungen ({inviteRooms.length})
						</p>
						{inviteRooms.map((room) => (
							<InviteItem key={room.roomId} room={room} client={client} onSelect={onSelect} />
						))}
					</div>
				)}
				{filteredRooms.length === 0 ? (
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
				) : (
					<div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
						{virtualizer.getVirtualItems().map((virtualRow) => {
							const room = filteredRooms[virtualRow.index];
							if (!room) return null;
							return (
								<div
									key={room.roomId}
									style={{
										position: "absolute",
										top: 0,
										left: 0,
										width: "100%",
										transform: `translateY(${virtualRow.start}px)`,
									}}
								>
									<RoomItem
										room={room}
										isSelected={room.roomId === selectedRoomId}
										onSelect={onSelect}
										client={client}
									/>
								</div>
							);
						})}
					</div>
				)}
			</div>
		</div>
	);
}

export const RoomList = memo(RoomListRaw);
