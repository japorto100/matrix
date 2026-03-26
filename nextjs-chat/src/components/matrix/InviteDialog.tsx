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
	roomId: string;
	trigger: React.ReactNode;
}

export function InviteDialog({ client, roomId, trigger }: Props) {
	const [open, setOpen] = useState(false);
	const [userId, setUserId] = useState("");
	const [isSending, setIsSending] = useState(false);

	async function submit() {
		const trimmedId = userId.trim();
		if (!trimmedId) return;

		setIsSending(true);
		try {
			await client.invite(roomId, trimmedId);
			setUserId("");
			setOpen(false);
		} catch (err) {
			console.error("[InviteDialog] failed:", err);
		} finally {
			setIsSending(false);
		}
	}

	const canSubmit = userId.trim().length > 0 && !isSending;

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>{trigger}</DialogTrigger>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle>Benutzer einladen</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col gap-3">
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Benutzer-ID
						</label>
						<input
							type="text"
							value={userId}
							onChange={(e) => setUserId(e.target.value)}
							placeholder="@benutzer:server.de"
							className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
						/>
					</div>
				</div>

				<DialogFooter>
					<Button variant="ghost" onClick={() => setOpen(false)}>
						Abbrechen
					</Button>
					<Button onClick={submit} disabled={!canSubmit}>
						{isSending ? "Sende…" : "Einladen"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
