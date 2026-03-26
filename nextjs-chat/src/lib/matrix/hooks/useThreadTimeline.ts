"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { ThreadEvent } from "matrix-js-sdk/lib/models/thread";
import { useCallback, useEffect, useState } from "react";
import { type ResolvedMessage, resolveMessage } from "@/lib/matrix/types";

const PAGE_SIZE = 50;

export interface UseThreadTimelineReturn {
	messages: ResolvedMessage[];
	isLoading: boolean;
	canLoadMore: boolean;
	loadMore: () => Promise<void>;
}

/** Reaktive Timeline für einen Thread. Mirrors useTimeline aber für thread.events. */
export function useThreadTimeline(
	client: MatrixClient | null,
	roomId: string | null,
	threadRootId: string | null,
): UseThreadTimelineReturn {
	const [messages, setMessages] = useState<ResolvedMessage[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [canLoadMore, setCanLoadMore] = useState(true);

	const buildMessages = useCallback(
		(roomIdArg: string, threadId: string) => {
			if (!client) return;
			const room = client.getRoom(roomIdArg);
			if (!room) return;
			const thread = room.getThread(threadId);
			if (!thread) return;

			const myId = client.getUserId() ?? "";
			const homeserverUrl = client.baseUrl;
			const timeline = thread.events;

			const replyLookup: Record<string, { sender: string; body: string }> = {};
			const resolved: ResolvedMessage[] = [];

			for (const ev of timeline) {
				const msg = resolveMessage(ev, myId, homeserverUrl, replyLookup);
				if (!msg) continue;
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

	useEffect(() => {
		if (!client || !roomId || !threadRootId) {
			setMessages([]);
			return;
		}

		const room = client.getRoom(roomId);
		const thread = room?.getThread(threadRootId);
		if (!thread) return;

		// Initiale Events laden falls noch nicht gefetched
		if (thread.events.length === 0) {
			client
				.paginateEventTimeline(thread.liveTimeline, { backwards: true, limit: PAGE_SIZE })
				.then(() => buildMessages(roomId, threadRootId))
				.catch((err) => console.warn("[threadTimeline] initial fetch failed:", err));
		} else {
			buildMessages(roomId, threadRootId);
		}

		function onNewReply() {
			buildMessages(roomId!, threadRootId!);
		}
		function onUpdate() {
			buildMessages(roomId!, threadRootId!);
		}

		thread.on(ThreadEvent.NewReply, onNewReply);
		thread.on(ThreadEvent.Update, onUpdate);

		return () => {
			thread.off(ThreadEvent.NewReply, onNewReply);
			thread.off(ThreadEvent.Update, onUpdate);
		};
	}, [client, roomId, threadRootId, buildMessages]);

	const loadMore = useCallback(async () => {
		if (!client || !roomId || !threadRootId || isLoading) return;
		const room = client.getRoom(roomId);
		const thread = room?.getThread(threadRootId);
		if (!thread) return;

		setIsLoading(true);
		try {
			const hasMore = await client.paginateEventTimeline(thread.liveTimeline, {
				backwards: true,
				limit: PAGE_SIZE,
			});
			buildMessages(roomId, threadRootId);
			setCanLoadMore(hasMore);
		} catch (err) {
			console.warn("[threadTimeline] paginate failed:", err);
			setCanLoadMore(false);
		} finally {
			setIsLoading(false);
		}
	}, [client, roomId, threadRootId, isLoading, buildMessages]);

	return { messages, isLoading, canLoadMore, loadMore };
}
