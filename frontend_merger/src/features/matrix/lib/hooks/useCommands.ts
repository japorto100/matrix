"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { useCallback } from "react";

export const SHRUG = "¯\\_(ツ)_/¯";
export const TABLEFLIP = "(╯°□°)╯︵ ┻━┻";
export const UNFLIP = "┬─┬ノ( º_ºノ)";

export type CommandOutcome =
	| { kind: "handled" }
	| { kind: "pass-through"; body: string; htmlBody?: string }
	| { kind: "error"; message: string };

/**
 * Parst eine User-Eingabe und fuehrt sie aus wenn es ein Slash-Command ist.
 *
 * Returns:
 *   - `null`                — keine Slash-Command-Syntax, normalen Send durchfuehren.
 *   - `{kind:"handled"}`     — Command wurde ausgefuehrt (sendEmote/kick/etc).
 *   - `{kind:"pass-through"}`— Command hat Text transformiert (e.g. /plain /html),
 *                              MessageComposer soll dann mit body/htmlBody senden.
 *   - `{kind:"error"}`       — Command-Ausfuehrung fehlgeschlagen, Toast anzeigen.
 *
 * Unterstuetzte Commands:
 *   /me <text>           Emote (m.emote)
 *   /shrug [text]        Anhaengt ¯\_(ツ)_/¯
 *   /tableflip [text]    Anhaengt (╯°□°)╯︵ ┻━┻
 *   /unflip [text]       Anhaengt ┬─┬ノ( º_ºノ)
 *   /plain <text>        Erzwingt Plain-Text-Send (kein formatted_body)
 *   /html <body>         Erzwingt HTML-Send (body=body, htmlBody=body)
 *   /kick <@user:...> [reason]    Kick User aus Raum
 *   /ban <@user:...> [reason]     Ban User aus Raum
 *   /unban <@user:...>            Unban User
 *   /invite <@user:...>           Einladung
 */
export async function executeCommand(
	client: MatrixClient,
	roomId: string,
	text: string,
): Promise<CommandOutcome | null> {
	if (!text.startsWith("/") || text.startsWith("//")) return null;

	const trimmed = text.slice(1);
	const firstSpace = trimmed.indexOf(" ");
	const command = (firstSpace === -1 ? trimmed : trimmed.slice(0, firstSpace)).toLowerCase();
	const payload = firstSpace === -1 ? "" : trimmed.slice(firstSpace + 1).trim();

	try {
		switch (command) {
			case "me": {
				if (!payload) return { kind: "error", message: "/me braucht einen Text" };
				await client.sendEmoteMessage(roomId, payload);
				return { kind: "handled" };
			}

			case "shrug":
				return { kind: "pass-through", body: payload ? `${payload} ${SHRUG}` : SHRUG };

			case "tableflip":
				return { kind: "pass-through", body: payload ? `${payload} ${TABLEFLIP}` : TABLEFLIP };

			case "unflip":
				return { kind: "pass-through", body: payload ? `${payload} ${UNFLIP}` : UNFLIP };

			case "plain": {
				if (!payload) return { kind: "error", message: "/plain braucht einen Text" };
				// Pass-through ohne htmlBody → MessageComposer sendet als plain text.
				return { kind: "pass-through", body: payload };
			}

			case "html": {
				if (!payload) return { kind: "error", message: "/html braucht einen HTML-Body" };
				await client.sendHtmlMessage(roomId, payload, payload);
				return { kind: "handled" };
			}

			case "kick": {
				const { userId, reason } = parseUserAndReason(payload);
				if (!userId) return { kind: "error", message: "/kick braucht @user:server" };
				await client.kick(roomId, userId, reason);
				return { kind: "handled" };
			}

			case "ban": {
				const { userId, reason } = parseUserAndReason(payload);
				if (!userId) return { kind: "error", message: "/ban braucht @user:server" };
				await client.ban(roomId, userId, reason);
				return { kind: "handled" };
			}

			case "unban": {
				const { userId } = parseUserAndReason(payload);
				if (!userId) return { kind: "error", message: "/unban braucht @user:server" };
				await client.unban(roomId, userId);
				return { kind: "handled" };
			}

			case "invite": {
				const { userId } = parseUserAndReason(payload);
				if (!userId) return { kind: "error", message: "/invite braucht @user:server" };
				await client.invite(roomId, userId);
				return { kind: "handled" };
			}

			default:
				return { kind: "error", message: `Unbekannter Befehl: /${command}` };
		}
	} catch (err) {
		return {
			kind: "error",
			message: err instanceof Error ? err.message : String(err),
		};
	}
}

/**
 * Zerlegt Payload wie `@user:server reason text` in userId + rest.
 * Matrix userIDs beginnen mit `@` und enthalten `:`.
 */
function parseUserAndReason(payload: string): { userId?: string; reason?: string } {
	if (!payload) return {};
	const firstSpace = payload.indexOf(" ");
	const first = firstSpace === -1 ? payload : payload.slice(0, firstSpace);
	if (!first.startsWith("@") || !first.includes(":")) return {};
	const reason = firstSpace === -1 ? undefined : payload.slice(firstSpace + 1).trim();
	return { userId: first, reason: reason || undefined };
}

/**
 * Hook-Wrapper fuer executeCommand. Bindet client+roomId, gibt stable callback.
 */
export function useCommands(client: MatrixClient | null, roomId: string | undefined) {
	return useCallback(
		async (text: string): Promise<CommandOutcome | null> => {
			if (!client || !roomId) return null;
			return executeCommand(client, roomId, text);
		},
		[client, roomId],
	);
}
