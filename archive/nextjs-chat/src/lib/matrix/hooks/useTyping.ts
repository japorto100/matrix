"use client";

import type { MatrixClient, RoomMember } from "matrix-js-sdk";
import { RoomMemberEvent } from "matrix-js-sdk";
import { useEffect, useState } from "react";

/** Gibt die Localparts der tippenden User zurück (exkl. eigene User-ID). */
export function useTyping(client: MatrixClient | null, roomId: string | null): string[] {
	const [typers, setTypers] = useState<string[]>([]);

	useEffect(() => {
		if (!client || !roomId) {
			setTypers([]);
			return;
		}

		function onTyping(_ev: unknown, member: RoomMember) {
			if (member.roomId !== roomId) return;

			const room = client!.getRoom(roomId!);
			if (!room) return;

			const myId = client!.getUserId() ?? "";
			const typing = room.currentState.getStateEvents("m.typing", "")?.getContent()?.user_ids as
				| string[]
				| undefined;

			const names = (typing ?? [])
				.filter((uid: string) => uid !== myId)
				.map((uid: string) => uid.split(":")[0]?.replace("@", "") ?? uid);

			setTypers(names);
		}

		client.on(RoomMemberEvent.Typing, onTyping);
		return () => {
			client.off(RoomMemberEvent.Typing, onTyping);
		};
	}, [client, roomId]);

	return typers;
}

/** Sendet Typing-Indikator-Event (debounced via Timeout im Caller). */
export async function sendTyping(
	client: MatrixClient,
	roomId: string,
	isTyping: boolean,
): Promise<void> {
	try {
		await client.sendTyping(roomId, isTyping, 5000);
	} catch {
		// ignorieren — nicht kritisch
	}
}
