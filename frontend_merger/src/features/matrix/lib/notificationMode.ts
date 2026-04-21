/**
 * Room-Level Notification-Mode via Matrix push-rules.
 *
 * Matrix push-rule Prioritaet: Override > Content > Room > Sender > Underride.
 * Diese Reihenfolge nutzen wir:
 *
 *   - `default`: keine custom Rules → Server-Default (underride m.room.rules etc.)
 *   - `all`: **override**-Rule mit Notify+Highlight-Tweaks → explicit notify,
 *     auch wenn global-quiet aktiv waere.
 *   - `mentions_keywords`: **room**-Rule mit DontNotify → generelle Messages
 *     notifizieren nicht. Mentions + Keywords werden weiterhin via **content**-
 *     Rules (hoehere Prio als room-Rules) getriggert.
 *   - `mute`: **override**-Rule mit DontNotify → blockt ALLES inkl. Mentions/
 *     Keywords (override > content).
 *
 * Backward-compat mit `useMuteRoom`: dessen boolean-toggleMute setzt weiterhin
 * die override-Rule mit DontNotify (= unser `mute`). `isMuted` in useMuteRoom
 * ist aequivalent zu `mode === "mute"`.
 */

import {
	type IPushRule,
	type IPushRules,
	PushRuleActionName,
	PushRuleKind,
	TweakName,
} from "matrix-js-sdk";

export type RoomNotificationMode = "default" | "all" | "mentions_keywords" | "mute";

/**
 * Ermittelt den aktuellen Mode eines Rooms aus der Push-Rules-Struktur.
 *
 * Pruefreihenfolge (Prio-absteigend):
 *  1. override[room_id] mit DontNotify → `mute`
 *  2. override[room_id] mit Notify → `all`
 *  3. room[room_id] mit DontNotify → `mentions_keywords`
 *  4. sonst → `default`
 */
export function getRoomNotificationMode(
	pushRules: IPushRules | undefined,
	roomId: string,
): RoomNotificationMode {
	if (!pushRules) return "default";

	const overrides = pushRules.global?.override ?? [];
	const rooms = pushRules.global?.room ?? [];

	const overrideRule = findRuleById(overrides, roomId);
	if (overrideRule && overrideRule.enabled !== false) {
		if (hasAction(overrideRule, PushRuleActionName.Notify)) return "all";
		if (hasAction(overrideRule, PushRuleActionName.DontNotify)) return "mute";
	}

	const roomRule = findRuleById(rooms, roomId);
	if (roomRule && roomRule.enabled !== false) {
		if (hasAction(roomRule, PushRuleActionName.DontNotify)) return "mentions_keywords";
	}

	return "default";
}

/**
 * Gibt fuer einen Mode die benoetigte Rule-Definition zurueck. `null` heisst
 * "keine Rule noetig" (= default, alle existierenden Rules fuer den room_id
 * muessen dann geloescht werden).
 */
export function getPushRuleForMode(
	mode: RoomNotificationMode,
	roomId: string,
): { kind: PushRuleKind; actions: IPushRule["actions"] } | null {
	if (mode === "default") return null;

	if (mode === "all") {
		return {
			kind: PushRuleKind.Override,
			actions: [
				PushRuleActionName.Notify,
				{ set_tweak: TweakName.Sound, value: "default" },
				{ set_tweak: TweakName.Highlight, value: false },
			],
		};
	}

	if (mode === "mentions_keywords") {
		return {
			kind: PushRuleKind.RoomSpecific,
			actions: [PushRuleActionName.DontNotify],
		};
	}

	// mute
	return {
		kind: PushRuleKind.Override,
		actions: [PushRuleActionName.DontNotify],
	};
}

/**
 * Welche kind(s) muessen beim Mode-Change vorher geloescht werden, damit keine
 * widerspruechlichen Rules existieren?
 *
 * Strategie: beim Mode-Change immer BEIDE kinds (Override + RoomSpecific) mit
 * dem room_id als rule_id loeschen, dann ggf. die neue anlegen.
 */
export function getAllRuleKindsForRoom(): PushRuleKind[] {
	return [PushRuleKind.Override, PushRuleKind.RoomSpecific];
}

function findRuleById(rules: IPushRule[], roomId: string): IPushRule | undefined {
	return rules.find((r) => r.rule_id === roomId);
}

function hasAction(rule: IPushRule, actionName: PushRuleActionName): boolean {
	return rule.actions.some(
		(a) => typeof a === "string" && (a as string) === (actionName as string),
	);
}
