"use client";

import type { MatrixClient, MatrixEvent, Room } from "matrix-js-sdk";
import { RoomEvent } from "matrix-js-sdk";
import { ThreadEvent } from "matrix-js-sdk/lib/models/thread";
import { useCallback, useEffect, useState } from "react";
import type { ResolvedMessage } from "@/lib/matrix/types";
import { mxcToHttp } from "@/lib/matrix/utils";
import { resolveMessage } from "@/lib/matrix/resolvers";

const PAGE_SIZE = 50;

export interface UseTimelineReturn {
	messages: ResolvedMessage[];
	isLoading: boolean;
	canLoadMore: boolean;
	loadMore: () => Promise<void>;
}

/** Reaktive Timeline für einen Raum. Unterstützt Pagination (loadMore). */
export function useTimeline(client: MatrixClient | null, roomId: string | null): UseTimelineReturn {
	const [messages, setMessages] = useState<ResolvedMessage[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [canLoadMore, setCanLoadMore] = useState(true);

	const buildMessages = useCallback(
		(roomIdArg: string) => {
			if (!client) return;
			const room = client.getRoom(roomIdArg);
			if (!room) return;

			const myId = client.getUserId() ?? "";
			const homeserverUrl = client.baseUrl;
			const timeline = room.getLiveTimeline().getEvents();

			// Reaktionen aggregieren (m.reaction events, redacted ignorieren)
			const reactionMap: Record<string, Record<string, number>> = {};
			// Alle eigenen Reactions pro Target-Event: { targetEventId → { emoji → reactionEventId } }
			const myReactionsMap: Record<string, Record<string, string>> = {};
			for (const ev of timeline) {
				if (ev.getType() !== "m.reaction") continue;
				if (ev.isRedacted()) continue;
				const content = ev.getContent() as Record<string, unknown>;
				const rel = content["m.relates_to"] as
					| { rel_type?: string; event_id?: string; key?: string }
					| undefined;
				if (rel?.rel_type === "m.annotation" && rel.event_id != null && rel.key != null) {
					if (!reactionMap[rel.event_id]) reactionMap[rel.event_id] = {};
					const existing = reactionMap[rel.event_id];
					if (existing) {
						existing[rel.key] = (existing[rel.key] ?? 0) + 1;
					}
					if (ev.getSender() === myId) {
						const myMap = myReactionsMap[rel.event_id] ?? {};
						myMap[rel.key] = ev.getId() ?? "";
						myReactionsMap[rel.event_id] = myMap;
					}
				}
			}

			// B-2: Read Receipts — wer hat welches Event zuletzt gelesen?
			const members = room.getJoinedMembers();
			const readByMap: Record<string, string[]> = {};
			for (const member of members) {
				if (member.userId === myId) continue;
				const receipt = room.getReadReceiptForUserId(member.userId);
				if (receipt?.eventId) {
					const list = readByMap[receipt.eventId] ?? [];
					list.push(member.userId);
					readByMap[receipt.eventId] = list;
				}
			}

			// B-8: Thread-Metadata (Reply-Count pro Thread-Root)
			const threadMap = new Map<string, number>();
			for (const thread of room.getThreads()) {
				threadMap.set(thread.id, thread.length);
			}

			// Reply-Lookup-Map (eventId → { sender, body }) für Reply-Kontext
			const replyLookup: Record<string, { sender: string; body: string }> = {};
			const resolved: ResolvedMessage[] = [];

			for (const ev of timeline) {
				const msg = resolveMessage(ev, myId, homeserverUrl, replyLookup);
				if (!msg) continue;

				// Reaktionen anfügen
				const rxns = reactionMap[msg.eventId];
				if (rxns) msg.reactions = rxns;
				const myRxns = myReactionsMap[msg.eventId];
				if (myRxns && Object.keys(myRxns).length > 0) {
					msg.myReactions = myRxns;
				}

				// Read Receipts anfügen
				const readers = readByMap[msg.eventId];
				if (readers?.length) msg.readBy = readers;

				// B-8: Thread-Root markieren
				const threadReplyCount = threadMap.get(msg.eventId);
				if (threadReplyCount !== undefined) {
					msg.isThreadRoot = true;
					msg.threadReplyCount = threadReplyCount;
				}

				// UI-11: Sender-Avatar auflösen
				const member = room.getMember(msg.sender);
				if (member?.getMxcAvatarUrl()) {
					msg.avatarUrl = mxcToHttp(member.getMxcAvatarUrl()!);
				}

				replyLookup[msg.eventId] = {
					sender: msg.senderDisplayName,
					body: msg.body,
				};
				resolved.push(msg);
			}

			setMessages(resolved);
		},
		[client],
	);

	// Raum wechsel → neu aufbauen
	useEffect(() => {
		if (!client || !roomId) {
			setMessages([]);
			return;
		}

		buildMessages(roomId);

		function onTimeline(_ev: MatrixEvent, room: Room | undefined) {
			if (room?.roomId === roomId) buildMessages(roomId!);
		}

		function onRedaction(_ev: MatrixEvent, room: Room | undefined) {
			if (room?.roomId === roomId) buildMessages(roomId!);
		}

		// B-2 Fix: Read Receipts reaktiv aktualisieren (debounced to avoid loops)
		let receiptTimer: ReturnType<typeof setTimeout> | null = null;
		function onReceipt(_ev: MatrixEvent, room: Room | undefined) {
			if (room?.roomId !== roomId) return;
			if (receiptTimer) clearTimeout(receiptTimer);
			receiptTimer = setTimeout(() => buildMessages(roomId!), 300);
		}

		// B-8: Thread-Update Listener für Reply-Count Aktualisierung
		function onThreadUpdate() {
			buildMessages(roomId!);
		}
		const room = client.getRoom(roomId);
		const threads = room?.getThreads() ?? [];
		for (const thread of threads) {
			thread.on(ThreadEvent.Update, onThreadUpdate);
		}

		client.on(RoomEvent.Timeline, onTimeline);
		client.on(RoomEvent.Redaction, onRedaction);
		client.on(RoomEvent.Receipt, onReceipt);

		return () => {
			if (receiptTimer) clearTimeout(receiptTimer);
			client.off(RoomEvent.Timeline, onTimeline);
			client.off(RoomEvent.Redaction, onRedaction);
			client.off(RoomEvent.Receipt, onReceipt);
			const cleanRoom = client.getRoom(roomId);
			for (const thread of cleanRoom?.getThreads() ?? []) {
				thread.off(ThreadEvent.Update, onThreadUpdate);
			}
		};
	}, [client, roomId, buildMessages]);

	const loadMore = useCallback(async () => {
		if (!client || !roomId || isLoading) return;

		const room = client.getRoom(roomId);
		if (!room) return;

		setIsLoading(true);
		try {
			await client.scrollback(room, PAGE_SIZE);
			buildMessages(roomId);
			const evCount = room.getLiveTimeline().getEvents().length;
			setCanLoadMore(evCount > 0);
		} catch (err) {
			console.warn("[timeline] scrollback failed:", err);
			setCanLoadMore(false);
		} finally {
			setIsLoading(false);
		}
	}, [client, roomId, isLoading, buildMessages]);

	return { messages, isLoading, canLoadMore, loadMore };
}
