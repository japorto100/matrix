"use client";

import type { MatrixClient } from "matrix-js-sdk";
import { ClientEvent, SyncState } from "matrix-js-sdk";
// SlidingSync ist nicht im Haupt-Export → interner Import
import { SlidingSync } from "matrix-js-sdk/lib/sliding-sync";
import { createContext, type ReactNode, useCallback, useEffect, useState } from "react";
import { destroyMatrixClient, getMatrixClient } from "@/lib/matrix/client";
import type { MatrixCredentials } from "@/lib/matrix/types";

interface MatrixContextValue {
	client: MatrixClient | null;
	myUserId: string;
	isReady: boolean;
	error: string | null;
}

export const MatrixContext = createContext<MatrixContextValue | null>(null);

interface Props {
	credentials: MatrixCredentials;
	children: ReactNode;
}

/**
 * Initialisiert den Matrix-Client und stellt ihn per Context bereit.
 * Muss innerhalb eines "use client"-Baums liegen und sollte nur einmal gerendert werden.
 */
export function MatrixProvider({ credentials, children }: Props) {
	const [client, setClient] = useState<MatrixClient | null>(null);
	const [isReady, setIsReady] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const init = useCallback(async () => {
		try {
			const mc = await getMatrixClient({
				homeserverUrl: credentials.homeserverUrl,
				userId: credentials.userId,
				accessToken: credentials.accessToken,
				deviceId: credentials.deviceId,
			});

			// C-1: Sliding Sync (MSC3575 / simplified_msc3575)
			// Tuwunel unterstützt /_matrix/client/unstable/org.matrix.simplified_msc3575/sync nativ.
			// Lädt nur sichtbare Räume → sub-500ms Initial-Load.
			// B-6: extensions.presence ist nicht in MSC3575List typisiert, daher any-Cast auf die Map
			// biome-ignore lint/suspicious/noExplicitAny: MSC3575List hat keine extensions-Typisierung
			const roomsList: any = {
				ranges: [[0, 99]],
				sort: ["by_notification_level", "by_recency"],
				timeline_limit: 50,
				required_state: [
					["m.room.name", ""],
					["m.room.topic", ""],
					["m.room.avatar", ""],
					["m.room.join_rules", ""],
					["m.room.history_visibility", ""],
					["m.room.encryption", ""],
					["m.room.power_levels", ""],
					["m.room.pinned_events", ""],
					["m.room.member", "$ME"],
				],
				extensions: {
					presence: { enabled: true },
				},
			};
			const slidingSync = new SlidingSync(
				credentials.homeserverUrl,
				new Map([["rooms", roomsList]]),
				// Default-Subscription für explizit abonnierte Räume (beim Raumwechsel)
				{
					timeline_limit: 100,
					required_state: [
						["m.room.member", "$LAZY"],
						["m.room.encryption", ""],
						["m.room.power_levels", ""],
						["m.room.pinned_events", ""],
					],
				},
				mc,
				30_000,
			);

			await mc.startClient({ slidingSync });

			// Warten bis Initial-Sync abgeschlossen (oder Fehler)
			await new Promise<void>((resolve, reject) => {
				if (mc.isInitialSyncComplete()) {
					resolve();
					return;
				}
				mc.once(ClientEvent.Sync, (state: SyncState) => {
					if (state === SyncState.Prepared || state === SyncState.Syncing) resolve();
					else if (state === SyncState.Error) reject(new Error("Sliding Sync fehlgeschlagen"));
				});
			});

			setClient(mc);
			setIsReady(true);
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			console.error("[MatrixProvider] init failed:", msg);
			setError(msg);
		}
	}, [credentials]);

	useEffect(() => {
		init();
		return () => {
			destroyMatrixClient();
			setClient(null);
			setIsReady(false);
		};
	}, [init]);

	return (
		<MatrixContext.Provider value={{ client, myUserId: credentials.userId, isReady, error }}>
			{children}
		</MatrixContext.Provider>
	);
}
