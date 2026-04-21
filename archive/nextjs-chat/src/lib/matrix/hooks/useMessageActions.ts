"use client";

import { EventType, type MatrixClient, RelationType } from "matrix-js-sdk";
import { useCallback } from "react";

/**
 * Hook fuer Message-Aktionen: React, Redact.
 * State-Setter (Reply, Edit, Forward, Thread) bleiben im Aufrufer.
 * Extrahiert aus MatrixChat (exec-07 Phase 5).
 */
export function useMessageActions(client: MatrixClient | null, roomId: string | null) {
	// B-3: Reaction senden (WhatsApp-Style: 1 pro User, Toggle, Replace)
	const handleReact = useCallback(
		async (eventId: string, emoji: string, myReactions?: Record<string, string>) => {
			if (!client || !roomId) return;

			const myExistingEventId = myReactions?.[emoji];

			// Dasselbe Emoji nochmal → entfernen (Toggle)
			if (myExistingEventId) {
				await client.redactEvent(roomId, myExistingEventId).catch(() => {});
				return;
			}

			// Alle bisherigen eigenen Reactions entfernen
			if (myReactions) {
				await Promise.all(
					Object.values(myReactions).map((id) => client.redactEvent(roomId, id).catch(() => {})),
				);
			}

			// Neue Reaction senden
			try {
				await client.sendEvent(roomId, EventType.Reaction, {
					"m.relates_to": { rel_type: RelationType.Annotation, event_id: eventId, key: emoji },
				});
			} catch (err) {
				console.error("[react] send failed:", err);
			}
		},
		[client, roomId],
	);

	// B-4: Nachricht loeschen (Redaction)
	const handleRedact = useCallback(
		(eventId: string) => {
			if (!client || !roomId) return;
			client.redactEvent(roomId, eventId).catch((err) => console.error("[redact] failed:", err));
		},
		[client, roomId],
	);

	return { handleReact, handleRedact };
}
