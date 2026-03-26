"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { ClientEvent, RoomEvent, RoomMemberEvent, UserEvent } from "matrix-js-sdk";
import { useEffect, useState } from "react";
import { type RoomInfo, resolveRoom } from "@/lib/matrix/types";

/** Reaktive Raumliste — aktualisiert sich bei Matrix-Events. */
export function useRooms(client: MatrixClient | null): RoomInfo[] {
	const [rooms, setRooms] = useState<RoomInfo[]>([]);

	useEffect(() => {
		if (!client) return;

		function refresh() {
			if (!client) return;
			const joined = client.getRooms().filter((r) => r.getMyMembership() === "join");
			const resolved = joined
				.map((r) => resolveRoom(r, client))
				.sort((a, b) => (b.lastTimestamp ?? 0) - (a.lastTimestamp ?? 0));
			setRooms(resolved);
		}

		refresh();

		client.on(ClientEvent.Room, refresh);
		client.on(RoomEvent.Timeline, refresh);
		client.on(RoomEvent.Name, refresh);
		client.on(RoomMemberEvent.Membership, refresh);
		// B-6: Presence-Updates
		client.on(UserEvent.CurrentlyActive, refresh);
		client.on(UserEvent.Presence, refresh);

		return () => {
			client.off(ClientEvent.Room, refresh);
			client.off(RoomEvent.Timeline, refresh);
			client.off(RoomEvent.Name, refresh);
			client.off(RoomMemberEvent.Membership, refresh);
			client.off(UserEvent.CurrentlyActive, refresh);
			client.off(UserEvent.Presence, refresh);
		};
	}, [client]);

	return rooms;
}
