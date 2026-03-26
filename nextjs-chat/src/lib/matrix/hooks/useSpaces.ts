"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { ClientEvent, RoomEvent, RoomMemberEvent } from "matrix-js-sdk";
import { useEffect, useState } from "react";

export interface SpaceInfo {
	roomId: string;
	name: string;
	childRoomIds: string[];
}

/** Reaktive Space-Liste — aktualisiert sich bei Matrix-Events. */
export function useSpaces(client: MatrixClient | null): {
	spaces: SpaceInfo[];
	isLoading: boolean;
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
				// Prüfe ob der Raum ein Space ist
				try {
					if (typeof r.isSpaceRoom === "function") return r.isSpaceRoom();
				} catch {
					// fallback
				}
				// Fallback: room type prüfen
				const createEvent = r.currentState.getStateEvents("m.room.create", "");
				const roomType = createEvent?.getContent()?.type;
				return roomType === "m.space";
			});

			const resolved: SpaceInfo[] = spaceRooms.map((space) => {
				// Child-Rooms aus m.space.child State Events
				const childEvents = space.currentState.getStateEvents("m.space.child");
				const childRoomIds = (Array.isArray(childEvents) ? childEvents : [])
					.filter((ev) => {
						const c = ev.getContent();
						// Ein leerer Content bedeutet dass das Kind entfernt wurde
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

			setSpaces(resolved.sort((a, b) => a.name.localeCompare(b.name)));
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

	return { spaces, isLoading };
}
