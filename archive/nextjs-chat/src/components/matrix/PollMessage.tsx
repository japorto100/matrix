"use client";

import { Loader2 } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { usePoll } from "@/lib/matrix/hooks/usePoll";
import { cn } from "@/lib/utils";

interface Props {
	pollEventId: string;
	roomId: string;
	client: MatrixClient;
	isOwn: boolean;
}

export function PollMessage({ pollEventId, roomId, client, isOwn }: Props) {
	const { question, answers, voteCounts, myVote, isEnded, totalVoters, isFetching, vote } = usePoll(
		client,
		roomId,
		pollEventId,
	);

	const maxVotes = Math.max(1, ...Object.values(voteCounts));

	return (
		<div
			className={cn(
				"rounded-2xl px-3 py-3 text-sm min-w-[220px] max-w-[320px]",
				isOwn ? "bg-primary text-primary-foreground rounded-tr-sm" : "bg-muted rounded-tl-sm",
			)}
		>
			<p className="font-semibold mb-2 leading-tight">{question || "Abstimmung"}</p>

			{isFetching && <Loader2 className="h-4 w-4 animate-spin my-2" />}

			<div className="flex flex-col gap-1.5">
				{answers.map((answer) => {
					const count = voteCounts[answer.id] ?? 0;
					const pct = totalVoters > 0 ? Math.round((count / maxVotes) * 100) : 0;
					const isMyVote = myVote.includes(answer.id);

					return (
						<button
							key={answer.id}
							type="button"
							disabled={isEnded}
							onClick={() => !isEnded && vote([answer.id])}
							className={cn(
								"relative w-full text-left px-2.5 py-1.5 rounded-lg border transition-colors overflow-hidden",
								isMyVote
									? isOwn
										? "border-primary-foreground/60 bg-primary-foreground/20"
										: "border-primary bg-primary/10"
									: isOwn
										? "border-primary-foreground/20 hover:bg-primary-foreground/10"
										: "border-border hover:bg-accent/50",
								isEnded && "cursor-default opacity-80",
							)}
						>
							<div
								className={cn(
									"absolute inset-0 rounded-lg transition-all duration-500",
									isOwn ? "bg-primary-foreground/10" : "bg-primary/8",
								)}
								style={{ width: `${pct}%` }}
							/>
							<div className="relative flex items-center justify-between gap-2">
								<span className="text-xs leading-tight">{answer.text}</span>
								<span className="text-[10px] opacity-70 shrink-0">
									{count > 0 ? `${count}` : ""}
								</span>
							</div>
						</button>
					);
				})}
			</div>

			<p className="text-[10px] opacity-60 mt-2">
				{isEnded ? "Abstimmung beendet" : `${totalVoters} Stimme${totalVoters !== 1 ? "n" : ""}`}
			</p>
		</div>
	);
}
