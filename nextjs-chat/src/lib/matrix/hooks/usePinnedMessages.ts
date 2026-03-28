"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { EventType, RoomStateEvent } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

/**
 * Hook fuer gepinnte Nachrichten — State, Live-Listener, Pin/Unpin, Power-Level Check.
 * Extrahiert aus MatrixChat + RoomInfoPanel (exec-07 Phase 4).
 */
export function usePinnedMessages(client: MatrixClient | null, roomId: string | null) {
	const [pinnedIds, setPinnedIds] = useState<string[]>([]);

	const room = roomId ? (client?.getRoom(roomId) ?? null) : null;

	// Pinned State lesen + Live-Listener
	useEffect(() => {
		if (!client || !room) {
			setPinnedIds([]);
			return;
		}
		const readPinned = () => {
			const pinned: string[] =
				room.currentState.getStateEvents(EventType.RoomPinnedEvents, "")?.getContent()?.pinned ??
				[];
			setPinnedIds(pinned);
		};
		readPinned();
		const handler = (_event: unknown, _room: unknown, type: string) => {
			if (type === EventType.RoomPinnedEvents) readPinned();
		};
		client.on(RoomStateEvent.Events, handler as any);
		return () => {
			client.off(RoomStateEvent.Events, handler as any);
		};
	}, [client, room]);

	// Power-Level Check: darf der User pinnen?
	const canPin = (() => {
		if (!client || !room) return false;
		const pl = room.currentState.getStateEvents("m.room.power_levels", "")?.getContent();
		const usersDefault = (pl?.users_default as number) ?? 0;
		const myPl =
			(pl?.users as Record<string, number> | undefined)?.[client.getUserId() ?? ""] ?? usersDefault;
		const pinLevel =
			(pl?.events as Record<string, number> | undefined)?.[EventType.RoomPinnedEvents] ??
			(pl?.state_default as number) ??
			50;
		return myPl >= pinLevel;
	})();

	// Pin/Unpin Toggle
	const togglePin = useCallback(
		(eventId: string) => {
			if (!client || !roomId) return;
			const currentRoom = client.getRoom(roomId);
			const pinnedEvent = currentRoom?.currentState.getStateEvents(EventType.RoomPinnedEvents, "");
			const currentPinned: string[] = pinnedEvent?.getContent()?.pinned ?? [];
			const isPinned = currentPinned.includes(eventId);
			const newPinned = isPinned
				? currentPinned.filter((id) => id !== eventId)
				: [...currentPinned, eventId];
			client
				.sendStateEvent(roomId, EventType.RoomPinnedEvents, { pinned: newPinned }, "")
				.then(() => toast.success(isPinned ? "Nachricht entpinnt." : "Nachricht angepinnt."))
				.catch((err) => {
					const msg = err?.data?.error?.includes("power level")
						? "Keine Berechtigung zum Pinnen."
						: "Pin fehlgeschlagen.";
					toast.error(msg);
				});
		},
		[client, roomId],
	);

	return { pinnedIds, canPin, togglePin };
}
