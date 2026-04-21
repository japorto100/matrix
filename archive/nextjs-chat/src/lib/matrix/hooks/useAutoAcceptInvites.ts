"use client";

import type { MatrixClient, Room } from "matrix-js-sdk";
import { RoomEvent } from "matrix-js-sdk";
import { useEffect } from "react";
import { toast } from "sonner";

const STORAGE_KEY = "matrix_auto_accept_dms";

/** Liest Auto-Accept Setting aus localStorage (default: true). */
export function getAutoAcceptDMs(): boolean {
	if (typeof window === "undefined") return true;
	const stored = localStorage.getItem(STORAGE_KEY);
	return stored === null ? true : stored === "true";
}

/** Setzt Auto-Accept Setting in localStorage. */
export function setAutoAcceptDMs(enabled: boolean): void {
	localStorage.setItem(STORAGE_KEY, String(enabled));
}

/**
 * Automatisch DM-Einladungen akzeptieren.
 * Gruppen-Einladungen zeigen einen Toast mit Annehmen/Ablehnen.
 */
export function useAutoAcceptInvites(client: MatrixClient | null): void {
	useEffect(() => {
		if (!client) return;

		const handler = (room: Room, membership: string, prevMembership?: string) => {
			if (membership !== "invite" || prevMembership === "invite") return;

			const dmInviter = room.getDMInviter();

			if (dmInviter && getAutoAcceptDMs()) {
				// DM → Auto-Accept
				client
					.joinRoom(room.roomId)
					.then(() => {
						toast.info(`Neue Direktnachricht von ${room.name}`);
					})
					.catch((err) => {
						console.error("[auto-accept] join failed:", err);
					});
			} else if (!dmInviter) {
				// Gruppen-Einladung → Toast mit Aktionen
				toast(`Einladung: ${room.name}`, {
					duration: 15000,
					action: {
						label: "Annehmen",
						onClick: () => {
							client.joinRoom(room.roomId).catch((err) => {
								console.error("[invite] join failed:", err);
								toast.error("Beitreten fehlgeschlagen.");
							});
						},
					},
					cancel: {
						label: "Ablehnen",
						onClick: () => {
							client.leave(room.roomId).catch(() => {});
						},
					},
				});
			}
		};

		client.on(RoomEvent.MyMembership, handler);
		return () => {
			client.off(RoomEvent.MyMembership, handler);
		};
	}, [client]);
}
