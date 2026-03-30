"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { NotificationCountType, RoomEvent } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { mxcToHttp } from "@/lib/matrix/utils";

export interface NotificationItem {
	id: string;
	type: "mention" | "invite" | "thread";
	roomId: string;
	roomName: string;
	senderName: string;
	senderAvatarUrl?: string;
	body: string;
	timestamp: number;
	/** Thread-Root Event ID (nur bei type=thread) */
	threadRootId?: string;
}

/**
 * Hook fuer Activity Centre — sammelt Mentions, Thread-Antworten, Invites.
 */
export function useNotifications(client: MatrixClient | null) {
	const [items, setItems] = useState<NotificationItem[]>([]);

	const refresh = useCallback(() => {
		if (!client) {
			setItems([]);
			return;
		}

		const myUserId = client.getUserId() ?? "";
		const result: NotificationItem[] = [];

		// 1. Invites
		for (const room of client.getRooms()) {
			if (room.getMyMembership() === "invite") {
				const inviter = room.getDMInviter() ?? "";
				result.push({
					id: `invite-${room.roomId}`,
					type: "invite",
					roomId: room.roomId,
					roomName: room.name ?? room.roomId,
					senderName: inviter.split(":")[0]?.replace("@", "") ?? inviter,
					body: "hat dich eingeladen",
					timestamp: Date.now(),
				});
			}
		}

		// 2. Mentions + Thread-Antworten aus Raeumen mit Highlights
		for (const room of client.getRooms()) {
			if (room.getMyMembership() !== "join") continue;
			const highlightCount = room.getUnreadNotificationCount(NotificationCountType.Highlight);
			if (!highlightCount || highlightCount <= 0) continue;

			// Letzte Events im Raum durchsuchen
			const events = room.getLiveTimeline().getEvents();
			for (let i = events.length - 1; i >= 0 && i >= events.length - 50; i--) {
				const ev = events[i];
				if (!ev || ev.getSender() === myUserId) continue;
				if (ev.getType() !== "m.room.message") continue;

				const content = ev.getContent();
				const mentions = content?.["m.mentions"] as { user_ids?: string[] } | undefined;
				const isMention = Array.isArray(mentions?.user_ids) && mentions.user_ids.includes(myUserId);
				const bodyText = (content?.body as string) ?? "";
				const isBodyMention =
					bodyText.includes(myUserId) || bodyText.includes(myUserId.split(":")[0] ?? "");

				// Thread-Antwort erkennen
				const relatesTo = content?.["m.relates_to"] as Record<string, unknown> | undefined;
				const isThread = relatesTo?.rel_type === "m.thread";
				const threadRootId = isThread ? (relatesTo?.event_id as string) : undefined;

				if (isMention || isBodyMention || isThread) {
					const sender = ev.getSender() ?? "";
					const member = room.getMember(sender);
					const mxcAvatar = member?.getMxcAvatarUrl();
					result.push({
						id: ev.getId() ?? `notif-${i}`,
						type: isThread && !isMention ? "thread" : "mention",
						roomId: room.roomId,
						roomName: room.name ?? room.roomId,
						senderName: member?.name ?? sender.split(":")[0]?.replace("@", "") ?? sender,
						senderAvatarUrl: mxcAvatar?.startsWith("mxc://") ? mxcToHttp(mxcAvatar) : undefined,
						body: bodyText.slice(0, 100),
						timestamp: ev.getTs(),
						threadRootId,
					});
				}
			}
		}

		// Sortieren: neueste zuerst
		result.sort((a, b) => b.timestamp - a.timestamp);
		setItems(result);
	}, [client]);

	useEffect(() => {
		if (!client) return;
		refresh();

		const onTimeline = () => refresh();
		client.on(RoomEvent.Timeline, onTimeline);
		return () => {
			client.off(RoomEvent.Timeline, onTimeline);
		};
	}, [client, refresh]);

	return { items, refresh };
}
