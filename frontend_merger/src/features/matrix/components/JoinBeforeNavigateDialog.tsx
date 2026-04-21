"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import { mxcToHttp } from "@matrix/lib/utils";
import type { MatrixClient, RoomSummary } from "matrix-js-sdk";
import { useEffect, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";

interface Props {
	client: MatrixClient;
	/** Room-ID oder Alias. `null` = Dialog geschlossen. */
	roomIdOrAlias: string | null;
	/** Via-Server fuer Federation-Discovery (optional). */
	viaServers?: string[];
	onClose: () => void;
	onJoined: (roomId: string) => void;
}

/**
 * Preview-Dialog vor Room-Join.
 *
 * Holt Public-Room-Summary (Name, Topic, Member-Count, Join-Rule) via
 * client.getRoomSummary() bevor der User zum Join committed. Schuetzt vor
 * versehentlichen Joins zu grossen Public-Rooms und zeigt wichtige
 * Meta-Infos (z.B. "invite-only") bereits im Dialog.
 *
 * Wird von Room-Permalink-Click-Handlern aufgerufen: Consumer setzt
 * `roomIdOrAlias`, Dialog laedt Summary, bei User-Bestaetigung fuehrt
 * joinRoom() aus und ruft `onJoined(roomId)`.
 */
export function JoinBeforeNavigateDialog({
	client,
	roomIdOrAlias,
	viaServers,
	onClose,
	onJoined,
}: Props) {
	const alive = useAlive();
	const [summary, setSummary] = useState<RoomSummary | null>(null);
	const [loading, setLoading] = useState(false);
	const [joining, setJoining] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!roomIdOrAlias) {
			setSummary(null);
			setError(null);
			return;
		}
		setLoading(true);
		setError(null);
		void (async () => {
			try {
				const s = await client.getRoomSummary(roomIdOrAlias, viaServers);
				if (alive()) setSummary(s);
			} catch (err) {
				if (alive()) setError(err instanceof Error ? err.message : String(err));
			} finally {
				if (alive()) setLoading(false);
			}
		})();
	}, [client, roomIdOrAlias, viaServers, alive]);

	const handleJoin = async () => {
		if (!roomIdOrAlias) return;
		setJoining(true);
		setError(null);
		try {
			const room = await client.joinRoom(roomIdOrAlias, { viaServers });
			if (alive()) onJoined(room.roomId);
		} catch (err) {
			if (alive()) setError(err instanceof Error ? err.message : String(err));
		} finally {
			if (alive()) setJoining(false);
		}
	};

	const avatarSrc = summary?.avatar_url ? mxcToHttp(summary.avatar_url) : undefined;

	return (
		<Dialog
			open={!!roomIdOrAlias}
			onOpenChange={(open) => {
				if (!open && !joining) onClose();
			}}
		>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Raum-Vorschau</DialogTitle>
				</DialogHeader>

				{loading && <div className="py-4 text-sm text-muted-foreground">Lade Raum-Info …</div>}

				{error && (
					<div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
				)}

				{summary && (
					<div className="space-y-3">
						<div className="flex items-center gap-3">
							<Avatar className="h-12 w-12">
								<AvatarImage src={avatarSrc} alt={summary.name ?? "Raum-Avatar"} />
								<AvatarFallback>{(summary.name ?? "?").charAt(0).toUpperCase()}</AvatarFallback>
							</Avatar>
							<div className="min-w-0 flex-1">
								<div className="truncate font-semibold">{summary.name ?? roomIdOrAlias}</div>
								<div className="text-xs text-muted-foreground">
									{summary.num_joined_members ?? "?"} Mitglieder
									{summary.join_rule && ` · ${summary.join_rule}`}
									{summary.room_type && ` · ${summary.room_type}`}
								</div>
							</div>
						</div>
						{summary.topic && (
							<p className="max-h-32 overflow-y-auto text-sm text-muted-foreground">
								{summary.topic}
							</p>
						)}
					</div>
				)}

				<DialogFooter>
					<Button variant="outline" onClick={onClose} disabled={joining}>
						Abbrechen
					</Button>
					<Button onClick={handleJoin} disabled={joining || loading || !summary}>
						{joining ? "Trete bei …" : "Beitreten"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
