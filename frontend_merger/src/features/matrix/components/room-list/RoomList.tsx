"use client";

import { monitorForElements } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import type { SpaceInfo } from "@matrix/lib/hooks/useSpaces";
import type { RoomInfo } from "@matrix/lib/types";
import { useVirtualizer } from "@tanstack/react-virtual";
import { MessageSquarePlus, Plus, Search } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { CreateRoomDialog } from "../CreateRoomDialog";
import { CreateDMDialog } from "../contacts/CreateDMDialog";
import { InviteItem } from "./InviteItem";
import { RoomGroupHeader } from "./RoomGroupHeader";
import { RoomItem } from "./RoomItem";

type GroupId = "invites" | "favourites" | "people" | "rooms" | "lowpriority";

const GROUP_ORDER: GroupId[] = ["invites", "favourites", "people", "rooms", "lowpriority"];
const GROUP_LABELS: Record<GroupId, string> = {
	invites: "Einladungen",
	favourites: "Favoriten",
	people: "Personen",
	rooms: "Räume",
	lowpriority: "Niedrige Priorität",
};

const COLLAPSE_STORAGE_KEY = "matrix.roomList.collapsedGroups";
const HEADER_HEIGHT = 26;
const ITEM_HEIGHT = 60;

type FlatItem =
	| { kind: "header"; groupId: GroupId; count: number; subLabel?: string }
	| { kind: "room"; room: RoomInfo; isInvite?: boolean };

interface Props {
	rooms: RoomInfo[];
	selectedRoomId: string | null;
	onSelect: (roomId: string) => void;
	isLoading?: boolean;
	client?: MatrixClient | null;
	spaces?: SpaceInfo[];
	selectedSpaceId?: string | null;
}

function loadCollapsed(): Set<GroupId> {
	if (typeof window === "undefined") return new Set();
	try {
		const raw = localStorage.getItem(COLLAPSE_STORAGE_KEY);
		if (!raw) return new Set();
		const parsed = JSON.parse(raw) as string[];
		return new Set(parsed.filter((g): g is GroupId => GROUP_ORDER.includes(g as GroupId)));
	} catch {
		return new Set();
	}
}

function saveCollapsed(set: Set<GroupId>) {
	if (typeof window === "undefined") return;
	try {
		localStorage.setItem(COLLAPSE_STORAGE_KEY, JSON.stringify([...set]));
	} catch {
		/* ignore */
	}
}

function categorize(room: RoomInfo): GroupId | null {
	if (room.membership === "invite") return "invites";
	if (room.membership !== "join") return null;
	if (room.isLowPriority) return "lowpriority";
	if (room.isFavourite) return "favourites";
	if (room.dmUserId) return "people";
	return "rooms";
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
	const [collapsed, setCollapsed] = useState<Set<GroupId>>(() => loadCollapsed());

	const selectedSpace = spaces?.find((s) => s.roomId === selectedSpaceId);

	// Lobby-DnD: Tag-Mutation bei Drop eines RoomItem auf einen RoomGroupHeader.
	// Latest rooms via Ref um stale-closure zu vermeiden ohne jeden rooms-Update
	// den Monitor neu zu registrieren.
	const roomsRef = useRef(rooms);
	roomsRef.current = rooms;
	useEffect(() => {
		if (!client) return;
		return monitorForElements({
			canMonitor: ({ source }) => source.data.type === "matrix.room-item",
			onDrop: async ({ source, location }) => {
				const target = location.current.dropTargets[0];
				if (!target) return;
				if (target.data.type !== "matrix.room-group") return;
				const targetGroup = target.data.groupId as GroupId;
				const roomId = source.data.roomId as string;
				// Same-Category-Guard: keine unnoetigen API-Calls wenn sich nichts aendert.
				const currentRoom = roomsRef.current.find((r) => r.roomId === roomId);
				if (currentRoom && categorize(currentRoom) === targetGroup) return;
				try {
					if (targetGroup === "favourites") {
						await client.deleteRoomTag(roomId, "m.lowpriority").catch(() => {});
						await client.setRoomTag(roomId, "m.favourite", { order: 0.5 });
						toast.success("Als Favorit markiert.");
					} else if (targetGroup === "lowpriority") {
						await client.deleteRoomTag(roomId, "m.favourite").catch(() => {});
						await client.setRoomTag(roomId, "m.lowpriority", { order: 0.5 });
						toast.success("Als niedrige Priorität markiert.");
					} else {
						// rooms / people: beide Tags entfernen → Default-Kategorie
						await client.deleteRoomTag(roomId, "m.favourite").catch(() => {});
						await client.deleteRoomTag(roomId, "m.lowpriority").catch(() => {});
						toast.success("Kategorie entfernt.");
					}
				} catch (err) {
					console.error("[RoomList] lobby-dnd failed:", err);
					toast.error("Verschieben fehlgeschlagen.");
				}
			},
		});
	}, [client]);

	const toggleGroup = useCallback((g: GroupId) => {
		setCollapsed((prev) => {
			const next = new Set(prev);
			if (next.has(g)) next.delete(g);
			else next.add(g);
			saveCollapsed(next);
			return next;
		});
	}, []);

	// Kategorisieren + Space-Intersection + Suche.
	const groups = useMemo<Record<GroupId, RoomInfo[]>>(() => {
		const buckets: Record<GroupId, RoomInfo[]> = {
			invites: [],
			favourites: [],
			people: [],
			rooms: [],
			lowpriority: [],
		};
		const q = search.trim().toLowerCase();
		for (const room of rooms) {
			if (selectedSpace && !selectedSpace.childRoomIds.includes(room.roomId)) continue;
			if (q && !room.name.toLowerCase().includes(q)) continue;
			const g = categorize(room);
			if (g) buckets[g].push(room);
		}
		return buckets;
	}, [rooms, selectedSpace, search]);

	// Flat-Virtualizer-Items: leere Gruppen werden ausgeblendet (Amendment #2).
	const flatItems = useMemo<FlatItem[]>(() => {
		const items: FlatItem[] = [];
		const subLabel = selectedSpace ? selectedSpace.name : undefined;
		for (const g of GROUP_ORDER) {
			const list = groups[g];
			if (list.length === 0) continue;
			items.push({
				kind: "header",
				groupId: g,
				count: list.length,
				subLabel: subLabel && (g === "favourites" || g === "lowpriority") ? subLabel : undefined,
			});
			if (collapsed.has(g)) continue;
			for (const room of list) {
				items.push({ kind: "room", room, isInvite: g === "invites" });
			}
		}
		return items;
	}, [groups, collapsed, selectedSpace]);

	// Navigierbare Room-Indices (Keyboard-Nav springt ueber Header — Amendment #6).
	const navigableIndices = useMemo(
		() => flatItems.map((it, i) => (it.kind === "room" ? i : -1)).filter((i) => i >= 0),
		[flatItems],
	);

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
		<aside
			className="w-72 border-r border-border/50 flex flex-col bg-sidebar shrink-0 overflow-hidden"
			data-matrix-roomlist
		>
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

				{totalUnread > 0 && (
					<p className="text-[10px] text-muted-foreground px-1">{totalUnread} ungelesen</p>
				)}
			</div>

			<FlatVirtualList
				items={flatItems}
				navigableIndices={navigableIndices}
				selectedRoomId={selectedRoomId}
				onSelect={onSelect}
				onToggleGroup={toggleGroup}
				collapsed={collapsed}
				client={client}
				emptyHint={
					search
						? "Keine Ergebnisse."
						: selectedSpace
							? "Keine Räume in diesem Space."
							: "Keine Chats."
				}
			/>
		</aside>
	);
}

interface FlatVirtualListProps {
	items: FlatItem[];
	navigableIndices: number[];
	selectedRoomId: string | null;
	onSelect: (roomId: string) => void;
	onToggleGroup: (g: GroupId) => void;
	collapsed: Set<GroupId>;
	client?: MatrixClient | null;
	emptyHint: string;
}

function FlatVirtualList({
	items,
	navigableIndices,
	selectedRoomId,
	onSelect,
	onToggleGroup,
	collapsed,
	client,
	emptyHint,
}: FlatVirtualListProps) {
	const scrollRef = useRef<HTMLDivElement>(null);
	const [inviteListRef] = useAutoAnimate<HTMLDivElement>();

	const virtualizer = useVirtualizer({
		count: items.length,
		getScrollElement: () => scrollRef.current,
		estimateSize: (index) => (items[index]?.kind === "header" ? HEADER_HEIGHT : ITEM_HEIGHT),
		overscan: 6,
	});

	// Arrow-Key-Nav springt ueber Header hinweg.
	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
			if (navigableIndices.length === 0) return;
			e.preventDefault();

			const currentFlatIdx = items.findIndex(
				(it) => it.kind === "room" && it.room.roomId === selectedRoomId,
			);
			const navPos = navigableIndices.indexOf(currentFlatIdx);

			let nextNavPos: number;
			if (navPos === -1) {
				nextNavPos = e.key === "ArrowDown" ? 0 : navigableIndices.length - 1;
			} else {
				nextNavPos =
					e.key === "ArrowDown"
						? Math.min(navPos + 1, navigableIndices.length - 1)
						: Math.max(navPos - 1, 0);
			}

			const nextFlatIdx = navigableIndices[nextNavPos];
			if (nextFlatIdx === undefined) return;
			const nextItem = items[nextFlatIdx];
			if (nextItem?.kind === "room") {
				onSelect(nextItem.room.roomId);
				virtualizer.scrollToIndex(nextFlatIdx, { align: "auto" });
			}
		},
		[items, navigableIndices, selectedRoomId, onSelect, virtualizer],
	);

	if (items.length === 0) {
		return (
			<div className="flex-1 overflow-y-auto">
				<p className="text-xs text-muted-foreground text-center py-8 px-4">{emptyHint}</p>
			</div>
		);
	}

	return (
		<div
			ref={scrollRef}
			className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-hide"
			onKeyDown={handleKeyDown}
			tabIndex={0}
			data-matrix-roomlist-scroll
		>
			{/* inviteListRef nur als stabiler Anchor — auto-animate wirkt auf direct children. */}
			<div ref={inviteListRef} className="px-2 pb-2">
				<div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
					{virtualizer.getVirtualItems().map((virtualRow) => {
						const item = items[virtualRow.index];
						if (!item) return null;
						const style = {
							position: "absolute" as const,
							top: 0,
							left: 0,
							width: "100%",
							transform: `translateY(${virtualRow.start}px)`,
						};
						if (item.kind === "header") {
							return (
								<div key={`h:${item.groupId}`} style={style}>
									<RoomGroupHeader
										label={GROUP_LABELS[item.groupId]}
										count={item.count}
										collapsed={collapsed.has(item.groupId)}
										onToggle={() => onToggleGroup(item.groupId)}
										highlightAmber={item.groupId === "invites"}
										subLabel={item.subLabel}
										groupId={item.groupId === "invites" ? undefined : item.groupId}
									/>
								</div>
							);
						}
						const { room, isInvite } = item;
						return (
							<div key={room.roomId} style={style}>
								{isInvite ? (
									<InviteItem room={room} client={client} onSelect={onSelect} />
								) : (
									<RoomItem
										room={room}
										isSelected={room.roomId === selectedRoomId}
										onSelect={onSelect}
										client={client}
									/>
								)}
							</div>
						);
					})}
				</div>
			</div>
		</div>
	);
}

export const RoomList = memo(RoomListRaw);
