"use client";

import {
	ConditionKind,
	EventType,
	type MatrixClient,
	PushRuleActionName,
	PushRuleKind,
} from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

/**
 * Hook fuer Raum-Stummschaltung via Push Rules.
 * Extrahiert aus RoomInfoPanel + DMInfoPanel (exec-07 Phase 4).
 */
export function useMuteRoom(client: MatrixClient | null, roomId: string | null) {
	const [isMuted, setIsMuted] = useState(false);

	useEffect(() => {
		if (!client || !roomId) return;
		try {
			const pushRules = client.getAccountData(EventType.PushRules)?.getContent();
			const overrides =
				(pushRules?.global as { override?: Array<{ rule_id: string; enabled: boolean }> })
					?.override ?? [];
			setIsMuted(!!overrides.find((r: { rule_id: string }) => r.rule_id === roomId)?.enabled);
		} catch {
			/* ignore */
		}
	}, [client, roomId]);

	const toggleMute = useCallback(async () => {
		if (!client || !roomId) return;
		try {
			if (isMuted) {
				await client.deletePushRule("global", PushRuleKind.Override, roomId);
			} else {
				await client.addPushRule("global", PushRuleKind.Override, roomId, {
					conditions: [{ kind: ConditionKind.EventMatch, key: "room_id", pattern: roomId }],
					actions: [PushRuleActionName.DontNotify],
				});
			}
			setIsMuted(!isMuted);
		} catch {
			toast.error("Stummschalten fehlgeschlagen.");
		}
	}, [client, roomId, isMuted]);

	return { isMuted, toggleMute };
}
