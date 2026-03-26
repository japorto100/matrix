"use client";

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
	trigger: React.ReactNode;
}

export function CreateRoomDialog({ client, trigger }: Props) {
	const [open, setOpen] = useState(false);
	const [name, setName] = useState("");
	const [topic, setTopic] = useState("");
	const [e2ee, setE2ee] = useState(true);
	const [isSending, setIsSending] = useState(false);

	async function submit() {
		const trimmedName = name.trim();
		if (!trimmedName) return;

		setIsSending(true);
		try {
			const opts: Record<string, unknown> = {
				name: trimmedName,
				preset: "private_chat",
				visibility: "private",
			};
			if (topic.trim()) opts.topic = topic.trim();
			if (e2ee) {
				opts.initial_state = [
					{
						type: "m.room.encryption",
						state_key: "",
						content: { algorithm: "m.megolm.v1.aes-sha2" },
					},
				];
			}
			await client.createRoom(opts);
			setName("");
			setTopic("");
			setE2ee(true);
			setOpen(false);
		} catch (err) {
			console.error("[CreateRoomDialog] failed:", err);
		} finally {
			setIsSending(false);
		}
	}

	const canSubmit = name.trim().length > 0 && !isSending;

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>{trigger}</DialogTrigger>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle>Raum erstellen</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col gap-3">
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Name (erforderlich)
						</label>
						<input
							type="text"
							value={name}
							onChange={(e) => setName(e.target.value)}
							placeholder="Raumname"
							className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
						/>
					</div>

					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Thema (optional)
						</label>
						<textarea
							value={topic}
							onChange={(e) => setTopic(e.target.value)}
							placeholder="Worum geht es in diesem Raum?"
							rows={2}
							className="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary"
						/>
					</div>

					<label className="flex items-center gap-2 text-sm cursor-pointer">
						<input
							type="checkbox"
							checked={e2ee}
							onChange={(e) => setE2ee(e.target.checked)}
							className="rounded border"
						/>
						Ende-zu-Ende-Verschlüsselung aktivieren
					</label>
				</div>

				<DialogFooter>
					<Button variant="ghost" onClick={() => setOpen(false)}>
						Abbrechen
					</Button>
					<Button onClick={submit} disabled={!canSubmit}>
						{isSending ? "Erstelle…" : "Raum erstellen"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
