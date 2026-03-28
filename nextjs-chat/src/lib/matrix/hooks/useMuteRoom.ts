"use client";

import type { MatrixClient } from "matrix-js-sdk";
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
			// biome-ignore lint/suspicious/noExplicitAny: push_rules nicht typisiert
			const pushRules = (client.getAccountData as any)("m.push_rules")?.getContent();
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
				// biome-ignore lint/suspicious/noExplicitAny: PushRuleKind nicht typisiert
				await (client.deletePushRule as any)("global", "override", roomId);
			} else {
				// biome-ignore lint/suspicious/noExplicitAny: PushRuleKind nicht typisiert
				await (client.addPushRule as any)("global", "override", roomId, {
					conditions: [{ kind: "event_match", key: "room_id", pattern: roomId }],
					actions: ["dont_notify"],
				});
			}
			setIsMuted(!isMuted);
		} catch {
			toast.error("Stummschalten fehlgeschlagen.");
		}
	}, [client, roomId, isMuted]);

	return { isMuted, toggleMute };
}
