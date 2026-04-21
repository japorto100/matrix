"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { PollEvent } from "matrix-js-sdk/lib/models/poll";
import type { Relations } from "matrix-js-sdk/lib/models/relations";
import { useCallback, useEffect, useState } from "react";

export interface PollAnswer {
	id: string;
	text: string;
}

export interface UsePollReturn {
	question: string;
	answers: PollAnswer[];
	voteCounts: Record<string, number>;
	myVote: string[];
	isEnded: boolean;
	totalVoters: number;
	isFetching: boolean;
	vote: (answerIds: string[]) => Promise<void>;
}

/** Last-vote-per-sender Deduplizierung (MSC3381 Spec: letzte Stimme pro Sender gewinnt). */
function deduplicateVotes(
	relations: Relations,
	myUserId: string,
): {
	voteCounts: Record<string, number>;
	myVote: string[];
	totalVoters: number;
} {
	const lastVoteByUser = new Map<string, { ts: number; answerIds: string[] }>();

	for (const ev of relations.getRelations() ?? []) {
		const sender = ev.getSender();
		if (!sender) continue;
		const content = ev.getContent() as Record<string, unknown>;
		const resp = (content["m.poll.response"] ?? content["org.matrix.msc3381.poll.response"]) as
			| { answers?: string[] }
			| undefined;
		const answerIds = resp?.answers ?? [];
		const ts = ev.getTs();
		const existing = lastVoteByUser.get(sender);
		if (!existing || ts > existing.ts) {
			lastVoteByUser.set(sender, { ts, answerIds });
		}
	}

	const voteCounts: Record<string, number> = {};
	let totalVoters = 0;
	let myVote: string[] = [];

	for (const [sender, { answerIds }] of lastVoteByUser) {
		if (answerIds.length === 0) continue;
		totalVoters++;
		for (const id of answerIds) {
			voteCounts[id] = (voteCounts[id] ?? 0) + 1;
		}
		if (sender === myUserId) myVote = answerIds;
	}

	return { voteCounts, myVote, totalVoters };
}

export function usePoll(
	client: MatrixClient | null,
	roomId: string | null,
	pollEventId: string | null,
): UsePollReturn {
	const [question, setQuestion] = useState("");
	const [answers, setAnswers] = useState<PollAnswer[]>([]);
	const [voteCounts, setVoteCounts] = useState<Record<string, number>>({});
	const [myVote, setMyVote] = useState<string[]>([]);
	const [isEnded, setIsEnded] = useState(false);
	const [totalVoters, setTotalVoters] = useState(0);
	const [isFetching, setIsFetching] = useState(false);

	const applyRelations = useCallback(
		(relations: Relations) => {
			if (!client) return;
			const myUserId = client.getUserId() ?? "";
			const result = deduplicateVotes(relations, myUserId);
			setVoteCounts(result.voteCounts);
			setMyVote(result.myVote);
			setTotalVoters(result.totalVoters);
		},
		[client],
	);

	useEffect(() => {
		if (!client || !roomId || !pollEventId) return;

		const room = client.getRoom(roomId);
		if (!room) return;

		const poll = room.polls.get(pollEventId);
		if (!poll) return;

		// Frage + Antworten aus dem SDK Poll-Model lesen
		setQuestion(poll.pollEvent.question.text ?? "");
		setAnswers(
			poll.pollEvent.answers.map((a) => ({
				id: a.id,
				text: a.text ?? "",
			})),
		);
		setIsEnded(poll.isEnded);

		// Initialer Fetch
		setIsFetching(true);
		poll
			.getResponses()
			.then((relations) => applyRelations(relations))
			.catch((err) => console.warn("[usePoll] getResponses failed:", err))
			.finally(() => setIsFetching(false));

		// Reaktive Updates
		function onResponses(relations: Relations) {
			applyRelations(relations);
		}
		function onEnd() {
			setIsEnded(true);
		}

		poll.on(PollEvent.Responses, onResponses);
		poll.on(PollEvent.End, onEnd);

		return () => {
			poll.off(PollEvent.Responses, onResponses);
			poll.off(PollEvent.End, onEnd);
		};
	}, [client, roomId, pollEventId, applyRelations]);

	const vote = useCallback(
		async (answerIds: string[]) => {
			if (!client || !roomId || !pollEventId) return;
			const { PollResponseEvent } = await import(
				"matrix-js-sdk/lib/extensible_events_v1/PollResponseEvent"
			);
			const responseEv = PollResponseEvent.from(answerIds, pollEventId);
			const serialized = responseEv.serialize();
			await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
				roomId,
				serialized.type,
				serialized.content,
			);
		},
		[client, roomId, pollEventId],
	);

	return { question, answers, voteCounts, myVote, isEnded, totalVoters, isFetching, vote };
}
