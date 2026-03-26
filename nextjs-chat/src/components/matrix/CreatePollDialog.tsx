"use client";

import { Plus, Trash2 } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";

interface Props {
	client: MatrixClient;
	roomId: string;
	trigger: React.ReactNode;
}

export function CreatePollDialog({ client, roomId, trigger }: Props) {
	const [open, setOpen] = useState(false);
	const [question, setQuestion] = useState("");
	const [answers, setAnswers] = useState(["", ""]);
	const [isSending, setIsSending] = useState(false);

	function addAnswer() {
		setAnswers((prev) => [...prev, ""]);
	}

	function removeAnswer(idx: number) {
		setAnswers((prev) => prev.filter((_, i) => i !== idx));
	}

	function updateAnswer(idx: number, value: string) {
		setAnswers((prev) => prev.map((a, i) => (i === idx ? value : a)));
	}

	async function submit() {
		const q = question.trim();
		const validAnswers = answers.map((a) => a.trim()).filter(Boolean);
		if (!q || validAnswers.length < 2) return;

		setIsSending(true);
		try {
			const { PollStartEvent } = await import(
				"matrix-js-sdk/lib/extensible_events_v1/PollStartEvent"
			);
			const { M_POLL_KIND_DISCLOSED } = await import("matrix-js-sdk/lib/@types/polls");

			const pollEv = PollStartEvent.from(q, validAnswers, M_POLL_KIND_DISCLOSED);
			const serialized = pollEv.serialize();

			await (client.sendEvent as (r: string, t: string, c: unknown) => Promise<unknown>)(
				roomId,
				serialized.type as string,
				serialized.content,
			);
			setQuestion("");
			setAnswers(["", ""]);
			setOpen(false);
		} catch (err) {
			console.error("[CreatePollDialog] send failed:", err);
		} finally {
			setIsSending(false);
		}
	}

	const canSubmit =
		question.trim().length > 0 && answers.filter((a) => a.trim()).length >= 2 && !isSending;

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>{trigger}</DialogTrigger>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle>Abstimmung erstellen</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col gap-3">
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">Frage</label>
						<input
							type="text"
							value={question}
							onChange={(e) => setQuestion(e.target.value)}
							placeholder="Worüber möchtest du abstimmen?"
							className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
						/>
					</div>

					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Antworten (min. 2)
						</label>
						<div className="flex flex-col gap-1.5">
							{answers.map((ans, idx) => (
								// biome-ignore lint/suspicious/noArrayIndexKey: Antworten haben keine stabile ID bis zum Senden
								<div key={idx} className="flex items-center gap-1.5">
									<input
										type="text"
										value={ans}
										onChange={(e) => updateAnswer(idx, e.target.value)}
										placeholder={`Antwort ${idx + 1}`}
										className="flex-1 rounded-md border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
									/>
									{answers.length > 2 && (
										<button
											type="button"
											onClick={() => removeAnswer(idx)}
											className="p-1 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
										>
											<Trash2 className="h-3.5 w-3.5" />
										</button>
									)}
								</div>
							))}
						</div>
						{answers.length < 10 && (
							<button
								type="button"
								onClick={addAnswer}
								className="mt-1.5 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
							>
								<Plus className="h-3 w-3" />
								Antwort hinzufügen
							</button>
						)}
					</div>
				</div>

				<DialogFooter>
					<Button variant="ghost" onClick={() => setOpen(false)}>
						Abbrechen
					</Button>
					<Button onClick={submit} disabled={!canSubmit}>
						{isSending ? "Sende…" : "Abstimmung starten"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
