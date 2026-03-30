"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { ClientEvent, RoomEvent, RoomMemberEvent } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";

export interface SpaceChildRoom {
	roomId: string;
	name: string;
	memberCount: number;
	isJoined: boolean;
	/** true wenn dieses Kind selbst ein Space ist (Sub-Space) */
	isSpace?: boolean;
}

export interface SpaceInfo {
	roomId: string;
	name: string;
	childRoomIds: string[];
	/** Server-seitige Hierarchie (inkl. ungejoinete Raeume). Nur gefuellt nach fetchHierarchy(). */
	hierarchy?: SpaceChildRoom[];
	/** Parent Space ID falls Sub-Space */
	parentSpaceId?: string;
}

/** Reaktive Space-Liste — aktualisiert sich bei Matrix-Events. */
export function useSpaces(client: MatrixClient | null): {
	spaces: SpaceInfo[];
	isLoading: boolean;
	fetchHierarchy: (spaceId: string) => Promise<void>;
} {
	const [spaces, setSpaces] = useState<SpaceInfo[]>([]);
	const [isLoading, setIsLoading] = useState(true);

	useEffect(() => {
		if (!client) {
			setSpaces([]);
			setIsLoading(false);
			return;
		}

		function refresh() {
			if (!client) return;
			const joined = client.getRooms().filter((r) => r.getMyMembership() === "join");
			const spaceRooms = joined.filter((r) => {
				try {
					if (typeof r.isSpaceRoom === "function") return r.isSpaceRoom();
				} catch {
					// fallback
				}
				const createEvent = r.currentState.getStateEvents("m.room.create", "");
				const roomType = createEvent?.getContent()?.type;
				return roomType === "m.space";
			});

			const resolved: SpaceInfo[] = spaceRooms.map((space) => {
				const childEvents = space.currentState.getStateEvents("m.space.child");
				const childRoomIds = (Array.isArray(childEvents) ? childEvents : [])
					.filter((ev) => {
						const c = ev.getContent();
						return c && Object.keys(c).length > 0;
					})
					.map((ev) => ev.getStateKey())
					.filter((id): id is string => !!id);

				return {
					roomId: space.roomId,
					name: space.name ?? space.roomId,
					childRoomIds,
				};
			});

			setSpaces((prev) => {
				// Behalte existierende hierarchy Daten bei refresh
				const hierarchyMap = new Map(prev.map((s) => [s.roomId, s.hierarchy]));
				return resolved
					.map((s) => ({ ...s, hierarchy: hierarchyMap.get(s.roomId) }))
					.sort((a, b) => a.name.localeCompare(b.name));
			});
			setIsLoading(false);
		}

		refresh();

		client.on(ClientEvent.Room, refresh);
		client.on(RoomEvent.Timeline, refresh);
		client.on(RoomEvent.Name, refresh);
		client.on(RoomMemberEvent.Membership, refresh);

		return () => {
			client.off(ClientEvent.Room, refresh);
			client.off(RoomEvent.Timeline, refresh);
			client.off(RoomEvent.Name, refresh);
			client.off(RoomMemberEvent.Membership, refresh);
		};
	}, [client]);

	/**
	 * Server-seitige Hierarchie laden (getRoomHierarchy).
	 * Zeigt auch Raeume die der User noch nicht gejoint hat.
	 */
	const fetchHierarchy = useCallback(
		async (spaceId: string) => {
			if (!client) return;
			try {
				// maxDepth=2 um Sub-Spaces zu erkennen
				const result = await client.getRoomHierarchy(spaceId, 50, 2, false);
				const joinedRoomIds = new Set(
					client
						.getRooms()
						.filter((r) => r.getMyMembership() === "join")
						.map((r) => r.roomId),
				);
				const children: SpaceChildRoom[] = (result.rooms ?? [])
					.filter((r) => r.room_id !== spaceId)
					.map((r) => ({
						roomId: r.room_id,
						name: r.name ?? r.room_id,
						memberCount: r.num_joined_members ?? 0,
						isJoined: joinedRoomIds.has(r.room_id),
						isSpace: r.room_type === "m.space",
					}));

				setSpaces((prev) =>
					prev.map((s) => (s.roomId === spaceId ? { ...s, hierarchy: children } : s)),
				);
			} catch (err) {
				console.warn("[useSpaces] getRoomHierarchy failed:", err);
			}
		},
		[client],
	);

	return { spaces, isLoading, fetchHierarchy };
}
