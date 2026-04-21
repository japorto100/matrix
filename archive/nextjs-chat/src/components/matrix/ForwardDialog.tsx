"use client";

import { Loader2 } from "lucide-react";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { RoomInfo } from "@/lib/matrix/types";

interface Props {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	client: MatrixClient;
	rooms: RoomInfo[];
	messageBody: string;
	senderName: string;
}

export function ForwardDialog({
	open,
	onOpenChange,
	client,
	rooms,
	messageBody,
	senderName,
}: Props) {
	const [isSending, setIsSending] = useState<string | null>(null);
	const [sent, setSent] = useState<Set<string>>(new Set());
	const [filter, setFilter] = useState("");

	const forwardTo = useCallback(
		async (targetRoomId: string) => {
			setIsSending(targetRoomId);
			try {
				await client.sendTextMessage(
					targetRoomId,
					`Weitergeleitet von ${senderName}:\n\n${messageBody}`,
				);
				setSent((prev) => new Set(prev).add(targetRoomId));
			} catch (err) {
				console.error("[ForwardDialog] forward failed:", err);
			} finally {
				setIsSending(null);
			}
		},
		[client, messageBody, senderName],
	);

	const filtered = rooms.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase()));

	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-md">
				<DialogHeader>
					<DialogTitle>Nachricht weiterleiten</DialogTitle>
				</DialogHeader>

				<div className="flex flex-col gap-3">
					<Input
						value={filter}
						onChange={(e) => setFilter(e.target.value)}
						placeholder="Raum suchen…"
					/>

					<div className="max-h-[300px] overflow-y-auto flex flex-col gap-1">
						{filtered.length === 0 && (
							<p className="text-sm text-muted-foreground text-center py-4">
								Keine Räume gefunden.
							</p>
						)}
						{filtered.map((room) => (
							<div
								key={room.roomId}
								className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted/50 transition-colors"
							>
								<span className="flex-1 text-sm truncate">{room.name}</span>
								{sent.has(room.roomId) ? (
									<span className="text-xs text-muted-foreground">Gesendet</span>
								) : (
									<Button
										size="sm"
										variant="outline"
										onClick={() => forwardTo(room.roomId)}
										disabled={isSending === room.roomId}
									>
										{isSending === room.roomId ? (
											<Loader2 className="h-3.5 w-3.5 animate-spin" />
										) : (
											"Senden"
										)}
									</Button>
								)}
							</div>
						))}
					</div>
				</div>
			</DialogContent>
		</Dialog>
	);
}
