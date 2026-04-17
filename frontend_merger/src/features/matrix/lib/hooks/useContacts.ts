"use client";

import { mxcToHttp } from "@matrix/lib/utils";
import { ClientEvent, EventType, type MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";

export interface Contact {
	userId: string;
	displayName: string;
	avatarUrl?: string;
	isOnline?: boolean;
	/** Timestamp der letzten DM-Aktivitaet (fuer Sortierung) */
	lastActive?: number;
	/** Ob dieser Contact aus der DM-Liste kommt (bekannter Kontakt) */
	isDmContact: boolean;
}

/**
 * Hook fuer Kontakte: bekannte DM-Kontakte + Server-Suche via User Directory.
 */
export function useContacts(client: MatrixClient | null) {
	const [dmContacts, setDmContacts] = useState<Contact[]>([]);

	// DM-Kontakte aus m.direct Account Data laden
	useEffect(() => {
		if (!client) {
			setDmContacts([]);
			return;
		}

		function loadDmContacts() {
			if (!client) return;
			const directEvent = client.getAccountData(EventType.Direct);
			const directMap: Record<string, string[]> = directEvent?.getContent() ?? {};
			const myUserId = client.getUserId() ?? "";

			const contacts: Contact[] = [];
			for (const [userId, roomIds] of Object.entries(directMap)) {
				if (userId === myUserId) continue;
				// Besten DM-Raum finden (gejoint, neuester)
				let lastActive = 0;
				for (const roomId of roomIds) {
					const room = client.getRoom(roomId);
					if (room?.getMyMembership() === "join") {
						const ts = room.getLastLiveEvent()?.getTs() ?? 0;
						if (ts > lastActive) lastActive = ts;
					}
				}

				const user = client.getUser(userId);
				const member = (() => {
					for (const roomId of roomIds) {
						const room = client.getRoom(roomId);
						const m = room?.getMember(userId);
						if (m) return m;
					}
					return null;
				})();

				const mxcAvatar = member?.getMxcAvatarUrl() ?? user?.avatarUrl;
				contacts.push({
					userId,
					displayName:
						member?.name ?? user?.displayName ?? userId.split(":")[0]?.replace("@", "") ?? userId,
					avatarUrl: mxcAvatar?.startsWith("mxc://") ? mxcToHttp(mxcAvatar) : undefined,
					isOnline: user?.currentlyActive ?? false,
					lastActive: lastActive || undefined,
					isDmContact: true,
				});
			}

			// Sortieren: zuletzt aktive zuerst
			contacts.sort((a, b) => (b.lastActive ?? 0) - (a.lastActive ?? 0));
			setDmContacts(contacts);
		}

		loadDmContacts();

		// Refresh bei neuen DMs
		const onAccountData = () => loadDmContacts();
		client.on(ClientEvent.AccountData, onAccountData);
		return () => {
			client.off(ClientEvent.AccountData, onAccountData);
		};
	}, [client]);

	/**
	 * Server-Suche via User Directory.
	 * Gibt Ergebnisse zurueck die NICHT in dmContacts sind.
	 */
	const searchUsers = useCallback(
		async (term: string, limit = 10): Promise<Contact[]> => {
			if (!client || !term.trim()) return [];
			try {
				const result = await client.searchUserDirectory({ term: term.trim(), limit });
				const myUserId = client.getUserId() ?? "";
				const dmUserIds = new Set(dmContacts.map((c) => c.userId));

				return (result.results ?? [])
					.filter((r) => r.user_id !== myUserId && !dmUserIds.has(r.user_id))
					.map((r) => ({
						userId: r.user_id,
						displayName: r.display_name ?? r.user_id.split(":")[0]?.replace("@", "") ?? r.user_id,
						avatarUrl: r.avatar_url?.startsWith("mxc://") ? mxcToHttp(r.avatar_url) : undefined,
						isDmContact: false,
					}));
			} catch (err) {
				console.warn("[useContacts] searchUserDirectory failed:", err);
				return [];
			}
		},
		[client, dmContacts],
	);

	return { dmContacts, searchUsers };
}
