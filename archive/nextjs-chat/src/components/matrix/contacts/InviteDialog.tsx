"use client";

import type { MatrixClient } from "matrix-js-sdk";
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
	roomId: string;
	trigger: React.ReactNode;
}

export function InviteDialog({ client, roomId, trigger }: Props) {
	const [open, setOpen] = useState(false);
	const [userId, setUserId] = useState("");
	const [isSending, setIsSending] = useState(false);

	async function submit(selectedUserId?: string) {
		const trimmedId = (selectedUserId ?? userId).trim();
		if (!trimmedId) return;

		setIsSending(true);
		try {
			await client.invite(roomId, trimmedId);
			toast.success(`${trimmedId} eingeladen.`);
			setUserId("");
			setOpen(false);
		} catch (err) {
			console.error("[InviteDialog] failed:", err);
			toast.error("Einladung fehlgeschlagen.");
		} finally {
			setIsSending(false);
		}
	}

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>{trigger}</DialogTrigger>
			<DialogContent className="max-w-md" aria-describedby={undefined}>
				<DialogHeader>
					<DialogTitle>Benutzer einladen</DialogTitle>
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
						{isSending ? "Sende..." : "Einladen"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
