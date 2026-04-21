"use client";

import { useAlive } from "@matrix/lib/hooks/useAlive";
import type { MatrixClient } from "matrix-js-sdk";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

export interface DeviceEntry {
	deviceId: string;
	displayName: string | null;
	lastSeenIp?: string;
	lastSeenTs?: number;
	isCurrent: boolean;
	isVerified: boolean;
}

export interface UseDevicesReturn {
	devices: DeviceEntry[];
	loading: boolean;
	error: string | null;
	refresh: () => Promise<void>;
	logoutDevice: (deviceId: string) => Promise<void>;
}

/**
 * G5: Wrapper um die SDK-Device-APIs.
 *
 * Holt via `client.getDevices()` die Session-Metadata (IPs, last-seen),
 * kombiniert mit Crypto-Trust-Info aus `crypto.getUserDeviceInfo(myUserId)`
 * fuer verified/unverified-Status.
 */
export function useDevices(client: MatrixClient | null): UseDevicesReturn {
	const alive = useAlive();
	const [devices, setDevices] = useState<DeviceEntry[]>([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const refresh = useCallback(async () => {
		if (!client) return;
		setLoading(true);
		setError(null);
		try {
			const [deviceList, myUserId] = [await client.getDevices(), client.getUserId()];
			const crypto = client.getCrypto();
			const currentDeviceId = client.getDeviceId();

			// Verified-Status via crypto-api (best-effort — falls Crypto nicht ready: alles unverified)
			let verifiedMap = new Map<string, boolean>();
			if (crypto && myUserId) {
				try {
					const devicesInfo = await crypto.getUserDeviceInfo([myUserId]);
					const userDevices = devicesInfo.get(myUserId);
					if (userDevices) {
						for (const [deviceId] of userDevices) {
							const status = await crypto.getDeviceVerificationStatus(myUserId, deviceId);
							verifiedMap.set(deviceId, status?.crossSigningVerified ?? false);
						}
					}
				} catch {
					verifiedMap = new Map();
				}
			}

			const entries: DeviceEntry[] = (deviceList.devices ?? []).map((d) => ({
				deviceId: d.device_id,
				displayName: d.display_name ?? null,
				lastSeenIp: d.last_seen_ip,
				lastSeenTs: d.last_seen_ts,
				isCurrent: d.device_id === currentDeviceId,
				isVerified: verifiedMap.get(d.device_id) ?? false,
			}));
			entries.sort((a, b) => {
				if (a.isCurrent) return -1;
				if (b.isCurrent) return 1;
				return (b.lastSeenTs ?? 0) - (a.lastSeenTs ?? 0);
			});

			if (alive()) setDevices(entries);
		} catch (err) {
			if (alive()) setError(err instanceof Error ? err.message : String(err));
		} finally {
			if (alive()) setLoading(false);
		}
	}, [client, alive]);

	useEffect(() => {
		void refresh();
	}, [refresh]);

	const logoutDevice = useCallback(
		async (deviceId: string) => {
			if (!client) return;
			try {
				// SDK 41: logoutSingleUserDevice braucht UIA-auth typisch. Wir nutzen die
				// simplest variant ohne UIA-Handler (Homeserver laesst's durch falls
				// recent gelogged-in) — sonst User muss via Element X abmelden.
				// biome-ignore lint/suspicious/noExplicitAny: SDK UIA-Handler kann auch null sein
				await (client as any).logoutSingleUserDevice?.(deviceId);
				toast.success("Geraet abgemeldet.");
				await refresh();
			} catch (err) {
				console.error("[useDevices] logout failed:", err);
				toast.error(
					"Abmeldung fehlgeschlagen — moeglicherweise UIA-Reauth erforderlich. Nutze die Account-Einstellungen im Homeserver.",
				);
			}
		},
		[client, refresh],
	);

	return { devices, loading, error, refresh, logoutDevice };
}
