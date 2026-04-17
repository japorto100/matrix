"use client";

import { EventType, type MatrixClient } from "matrix-js-sdk";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";
import { ContactPicker } from "./ContactPicker";

interface Props {
	client: MatrixClient;
	trigger: React.ReactNode;
}

export function CreateDMDialog({ client, trigger }: Props) {
	const [open, setOpen] = useState(false);
	const [userId, setUserId] = useState("");
	const [isSending, setIsSending] = useState(false);

	async function submit(selectedUserId?: string) {
		const trimmedId = (selectedUserId ?? userId).trim();
		if (!trimmedId) return;

		setIsSending(true);
		try {
			const { Preset } = await import("matrix-js-sdk/lib/@types/partials");
			const result = await client.createRoom({
				is_direct: true,
				invite: [trimmedId],
				preset: Preset.TrustedPrivateChat,
			});

			// m.direct Account-Data setzen damit der Raum als DM erkannt wird
			try {
				const directEvent = client.getAccountData(EventType.Direct);
				const directMap: Record<string, string[]> = directEvent?.getContent() ?? {};
				const existing = directMap[trimmedId] ?? [];
				if (!existing.includes(result.room_id)) {
					directMap[trimmedId] = [...existing, result.room_id];
					await client.setAccountData(EventType.Direct, directMap);
				}
			} catch {
				// m.direct setzen ist optional
			}

			toast.success(`Chat mit ${trimmedId} gestartet.`);
			setUserId("");
			setOpen(false);
		} catch (err) {
			console.error("[CreateDMDialog] failed:", err);
			toast.error("Direktnachricht konnte nicht erstellt werden.");
		} finally {
			setIsSending(false);
		}
	}

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>{trigger}</DialogTrigger>
			<DialogContent className="max-w-md" aria-describedby={undefined}>
				<DialogHeader>
					<DialogTitle>Direktnachricht starten</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col gap-3">
					<ContactPicker
						client={client}
						value={userId}
						onChange={setUserId}
						onSelect={(id) => submit(id)}
						placeholder="Name oder @user:server suchen"
						autoFocus
					/>
				</div>

				<DialogFooter>
					<Button variant="ghost" onClick={() => setOpen(false)}>
						Abbrechen
					</Button>
					<Button onClick={() => submit()} disabled={!userId.trim() || isSending}>
						{isSending ? "Sende..." : "Nachricht starten"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
