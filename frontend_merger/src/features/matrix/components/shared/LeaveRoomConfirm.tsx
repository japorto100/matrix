"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import type { MatrixClient } from "matrix-js-sdk";
import { useState } from "react";
import { toast } from "sonner";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface Props {
	client: MatrixClient;
	/** Zu verlassender Room. `null` = Dialog geschlossen. */
	roomId: string | null;
	roomName?: string;
	/** Nach erfolgreichem Leave. */
	onLeft?: () => void;
	onClose: () => void;
}

/**
 * Simple Confirm-Dialog vor `client.leave(roomId)`.
 *
 * Accidental-Click-Guard fuer Leave-Aktionen im RoomList-Context-Menu,
 * Invite-UI und anderen Oberflaechen. Fuer **admin-delete-Flow** (kick alle
 * Members + leave + forget) nutzt RoomInfoPanel einen eigenen inline-2-step
 * Confirm im Footer, da das Layout dort anders ist.
 *
 * Nach Leave: calls `client.forget(roomId)` (best-effort) damit der Room
 * aus den lokalen Matrix-Stores verschwindet und nicht wieder in der Liste
 * auftaucht.
 */
export function LeaveRoomConfirm({ client, roomId, roomName, onLeft, onClose }: Props) {
	const alive = useAlive();
	const [leaving, setLeaving] = useState(false);

	const handleConfirm = async () => {
		if (!roomId) return;
		setLeaving(true);
		try {
			await client.leave(roomId);
			await client.forget(roomId).catch(() => {
				// forget ist best-effort — leave ist wichtiger
			});
			if (alive()) {
				onLeft?.();
				onClose();
			}
		} catch (err) {
			console.error("[leave-room] leave failed:", err);
			toast.error("Raum konnte nicht verlassen werden.");
		} finally {
			if (alive()) setLeaving(false);
		}
	};

	return (
		<AlertDialog
			open={!!roomId}
			onOpenChange={(o) => {
				if (!o && !leaving) onClose();
			}}
		>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle>Raum verlassen?</AlertDialogTitle>
					<AlertDialogDescription>
						Du verlaesst <strong>{roomName ?? roomId}</strong>. Du kannst spaeter wieder beitreten,
						wenn du eine Einladung bekommst oder der Raum oeffentlich ist. Alte Nachrichten koennen
						dir nur wieder sichtbar werden, wenn History-Visibility entsprechend gesetzt war.
					</AlertDialogDescription>
				</AlertDialogHeader>
				<AlertDialogFooter>
					<AlertDialogCancel disabled={leaving}>Abbrechen</AlertDialogCancel>
					<AlertDialogAction
						onClick={(e) => {
							e.preventDefault();
							void handleConfirm();
						}}
						disabled={leaving}
						className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
					>
						{leaving ? "Verlasse…" : "Verlassen"}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
