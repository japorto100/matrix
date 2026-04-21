"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { ClientEvent, RoomEvent, RoomMemberEvent, UserEvent } from "matrix-js-sdk";
import { useEffect, useRef, useState } from "react";
import { type RoomInfo, resolveRoom } from "@/lib/matrix/types";

/** Returns true if two RoomInfo objects are identical field-by-field. */
function roomInfoEqual(a: RoomInfo, b: RoomInfo): boolean {
	return (
		a.roomId === b.roomId &&
		a.name === b.name &&
		a.topic === b.topic &&
		a.memberCount === b.memberCount &&
		a.unreadCount === b.unreadCount &&
		a.lastMessage === b.lastMessage &&
		a.lastTimestamp === b.lastTimestamp &&
		a.avatarUrl === b.avatarUrl &&
		a.dmUserId === b.dmUserId &&
		a.membership === b.membership &&
		a.isOnline === b.isOnline &&
		a.isFavourite === b.isFavourite
	);
}

/** Reaktive Raumliste — aktualisiert sich bei Matrix-Events. */
export function useRooms(client: MatrixClient | null): RoomInfo[] {
	const [rooms, setRooms] = useState<RoomInfo[]>([]);
	// Keep a ref to the latest rooms so refresh() can compare without a stale closure.
	const roomsRef = useRef<RoomInfo[]>([]);

	useEffect(() => {
		if (!client) return;

		function refresh() {
			if (!client) return;
			// Join + Invite Rooms anzeigen (leave/ban ausblenden)
			const visible = client
				.getRooms()
				.filter((r) => ["join", "invite"].includes(r.getMyMembership()));
			const next = visible
				.map((r) => resolveRoom(r, client))
				.sort((a, b) => (b.lastTimestamp ?? 0) - (a.lastTimestamp ?? 0));

			// Build a stable array: reuse existing RoomInfo objects for rooms that
			// haven't changed so that React.memo on RoomList (and its children) can
			// bail out when only the user's own profile was updated.
			const prev = roomsRef.current;
			const prevById = new Map<string, RoomInfo>(prev.map((r) => [r.roomId, r]));

			let changed = next.length !== prev.length;
			const resolved = next.map((newRoom) => {
				const old = prevById.get(newRoom.roomId);
				if (old && roomInfoEqual(old, newRoom)) {
					return old; // stable reference — nothing changed for this room
				}
				changed = true;
				return newRoom;
			});

			// Only trigger a re-render when something actually changed.
			if (!changed) return;

			roomsRef.current = resolved;
			setRooms(resolved);
		}

		refresh();

		client.on(ClientEvent.Room, refresh);
		client.on(ClientEvent.DeleteRoom, refresh);
		client.on(RoomEvent.Timeline, refresh);
		client.on(RoomEvent.Name, refresh);
		client.on(RoomEvent.Tags, refresh);
		client.on(RoomEvent.MyMembership, refresh);
		client.on(RoomMemberEvent.Membership, refresh);
		client.on(UserEvent.CurrentlyActive, refresh);
		client.on(UserEvent.Presence, refresh);

		return () => {
			client.off(ClientEvent.Room, refresh);
			client.off(ClientEvent.DeleteRoom, refresh);
			client.off(RoomEvent.Timeline, refresh);
			client.off(RoomEvent.Name, refresh);
			client.off(RoomEvent.Tags, refresh);
			client.off(RoomEvent.MyMembership, refresh);
			client.off(RoomMemberEvent.Membership, refresh);
			client.off(UserEvent.CurrentlyActive, refresh);
			client.off(UserEvent.Presence, refresh);
		};
	}, [client]);

	return rooms;
}
