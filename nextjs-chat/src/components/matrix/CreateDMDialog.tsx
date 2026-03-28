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
import { Input } from "@/components/ui/input";

interface Props {
	client: MatrixClient;
	trigger: React.ReactNode;
}

export function CreateDMDialog({ client, trigger }: Props) {
	const [open, setOpen] = useState(false);
	const [userId, setUserId] = useState("");
	const [isSending, setIsSending] = useState(false);

	async function submit() {
		const trimmedId = userId.trim();
		if (!trimmedId) return;

		setIsSending(true);
		try {
			// DMs unverschlüsselt bis exec-05 (Go Appservice E2EE aktiviert)
			const { Preset } = await import("matrix-js-sdk/lib/@types/partials");
			const result = await client.createRoom({
				is_direct: true,
				invite: [trimmedId],
				preset: Preset.TrustedPrivateChat,
			});

			// m.direct Account-Data setzen damit der Raum als DM erkannt wird
			try {
				// biome-ignore lint/suspicious/noExplicitAny: m.direct nicht in SDK-Typen
				const directEvent = (client.getAccountData as any)("m.direct");
				const directMap: Record<string, string[]> = directEvent?.getContent() ?? {};
				const existing = directMap[trimmedId] ?? [];
				if (!existing.includes(result.room_id)) {
					directMap[trimmedId] = [...existing, result.room_id];
					// biome-ignore lint/suspicious/noExplicitAny: m.direct nicht in SDK-Typen
					await (client.setAccountData as any)("m.direct", directMap);
				}
			} catch {
				// m.direct setzen ist optional, kein Fehler wenn es fehlschlägt
			}

			setUserId("");
			setOpen(false);
		} catch (err) {
			console.error("[CreateDMDialog] failed:", err);
			toast.error("Direktnachricht konnte nicht erstellt werden.");
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
					<DialogTitle>Direktnachricht starten</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col gap-3">
					<div>
						<label className="text-xs font-medium text-muted-foreground mb-1 block">
							Benutzer-ID
						</label>
						<Input
							value={userId}
							onChange={(e) => setUserId(e.target.value)}
							placeholder="@benutzer:server.de"
						/>
					</div>
				</div>

				<DialogFooter>
					<Button variant="ghost" onClick={() => setOpen(false)}>
						Abbrechen
					</Button>
					<Button onClick={submit} disabled={!canSubmit}>
						{isSending ? "Sende…" : "Nachricht starten"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
