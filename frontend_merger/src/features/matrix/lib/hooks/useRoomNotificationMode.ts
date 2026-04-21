"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import {
	getAllRuleKindsForRoom,
	getPushRuleForMode,
	getRoomNotificationMode,
	type RoomNotificationMode,
} from "@matrix/lib/notificationMode";
import { ClientEvent, EventType, type IPushRules, type MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

export interface UseRoomNotificationModeReturn {
	mode: RoomNotificationMode;
	isSetting: boolean;
	setMode: (next: RoomNotificationMode) => Promise<void>;
}

/**
 * 4-state Notification-Mode per Room.
 *
 * Reaktiv via `ClientEvent.AccountData`-Listener — push_rules-Aenderungen
 * (lokal oder von anderen Clients) werden sofort reflektiert.
 *
 * `setMode` loescht bestehende override+room Rules fuer den roomId und legt
 * ggf. die neue an. `default` loescht nur.
 */
export function useRoomNotificationMode(
	client: MatrixClient | null,
	roomId: string | null,
): UseRoomNotificationModeReturn {
	const alive = useAlive();
	const [mode, setModeState] = useState<RoomNotificationMode>("default");
	const [isSetting, setIsSetting] = useState(false);

	const recompute = useCallback(() => {
		if (!client || !roomId) return;
		try {
			const pushRules = client.getAccountData(EventType.PushRules)?.getContent<IPushRules>();
			setModeState(getRoomNotificationMode(pushRules, roomId));
		} catch {
			setModeState("default");
		}
	}, [client, roomId]);

	useEffect(() => {
		recompute();
		if (!client) return;
		const handler = () => recompute();
		client.on(ClientEvent.AccountData, handler);
		return () => {
			client.off(ClientEvent.AccountData, handler);
		};
	}, [client, recompute]);

	const setMode = useCallback(
		async (next: RoomNotificationMode) => {
			if (!client || !roomId) return;
			setIsSetting(true);
			try {
				// Alle existierenden Rules (override + room) fuer diesen roomId loeschen
				// — verhindert widerspruechliche States.
				for (const kind of getAllRuleKindsForRoom()) {
					await client.deletePushRule("global", kind, roomId).catch(() => {
						// Rule existiert vielleicht nicht — kein Error.
					});
				}

				// Neue Rule anlegen (falls != default)
				const rule = getPushRuleForMode(next, roomId);
				if (rule) {
					await client.addPushRule("global", rule.kind, roomId, {
						actions: rule.actions,
					});
				}

				if (alive()) setModeState(next);
			} catch (err) {
				console.error("[useRoomNotificationMode] setMode failed:", err);
				toast.error("Benachrichtigungs-Modus konnte nicht gesetzt werden.");
			} finally {
				if (alive()) setIsSetting(false);
			}
		},
		[client, roomId, alive],
	);

	return { mode, isSetting, setMode };
}
